package pl.gps.pozycja;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Notification;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;

/**
 * Usługa działająca w trakcie jazdy: śledzi GPS i po zakończeniu jazdy zapisuje
 * miejsce parkowania. GPS jest włączony tylko w trakcie jazdy.
 *
 * <p>Początek i koniec jazdy zgłasza {@link CarBluetoothReceiver}: połączenie / rozłączenie
 * z Bluetooth auta. Rozłączenie następuje przy wyłączeniu silnika, więc wiemy dokładnie,
 * kiedy auto stanęło. Gdyby rozłączenie nie dotarło, o końcu jazdy decyduje
 * {@link DrivePolicy} ({@link #SOURCE_TIMEOUT}).
 *
 * <p>Zasada: pozycja ustalona po fakcie to miejsce, w którym stoi kierowca, a nie auto.
 * Pozycje sprzed zdarzenia o więcej niż {@link #CACHED_FIX_WINDOW_MS} odrzucamy, bo mogą
 * pochodzić z trasy (nawet kilometry od parkingu).
 */
public class DrivingService extends Service {

    static final String ACTION_DRIVING_STARTED = "pl.gps.pozycja.DRIVING_STARTED";
    static final String ACTION_DRIVING_ENDED = "pl.gps.pozycja.DRIVING_ENDED";
    static final String ACTION_CANCEL = "pl.gps.pozycja.DRIVING_CANCEL";

    static final String EXTRA_SOURCE = "source";
    /** Czas zdarzenia w {@link SystemClock#elapsedRealtime()} (ms). */
    static final String EXTRA_EVENT_TIME = "eventTime";
    /** Koniec jazdy ustalony przez usługę (brak jazdy od dłuższego czasu), a nie przez zdarzenie. */
    static final String SOURCE_TIMEOUT = "timeout";
    static final String SOURCE_BLUETOOTH = "bluetooth";

    private static final long GPS_INTERVAL_MS = 2000;
    /** Po zgłoszeniu końca jazdy bez danych z jazdy czekamy tyle na aktualną pozycję. */
    private static final long WAIT_FOR_FIX_MS = 45_000;
    /** Zapamiętana przez system pozycja jest użyteczna tylko, jeśli pochodzi z okolic zdarzenia. */
    static final long CACHED_FIX_WINDOW_MS = 60_000;
    /** Pomiar z chwili rozłączenia Bluetooth może być najwyżej tyle starszy od zdarzenia. */
    private static final long BLUETOOTH_FIX_MAX_GAP_MS = 30_000;
    /** Rozłączenie Bluetooth, gdy auto jechało w ostatnich tylu ms, to chwilowe zerwanie, a nie parking. */
    private static final long BLUETOOTH_GLITCH_WINDOW_MS = 10_000;
    /** Po zdarzeniu rozpoznawania aktywności starszym niż to nie szukamy już nowej pozycji. */
    private static final long LATE_EVENT_MS = 2 * 60_000L;
    private static final float MAX_SAVE_ACCURACY_M = 100f;

    /** Stan widoczny dla ekranu aplikacji (ten sam proces). */
    static volatile boolean running;
    static volatile boolean driving;

    private final ParkingDetector detector = new ParkingDetector();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private LocationManager locationManager;
    private boolean updatesRunning;
    private boolean waitingForFix;
    private boolean loggedDriving;
    private long startedAtMs;

    // ------------------------------------------------------------------ start z zewnątrz

    /**
     * Uruchamia usługę z odbiornika zdarzeń. Zwraca false, jeśli system nie pozwolił
     * jej uruchomić (wtedy wołający powinien zapisać pozycję w inny sposób).
     */
    static boolean start(Context c, String action, String source, long eventTimeMs) {
        Intent i = new Intent(c, DrivingService.class).setAction(action)
                .putExtra(EXTRA_SOURCE, source)
                .putExtra(EXTRA_EVENT_TIME, eventTimeMs);
        try {
            if (Build.VERSION.SDK_INT >= 26) {
                c.startForegroundService(i);
            } else {
                c.startService(i);
            }
            return true;
        } catch (IllegalStateException | SecurityException e) {
            // np. ForegroundServiceStartNotAllowedException (Android 12+)
            return false;
        }
    }

    static void cancel(Context c) {
        if (!running) return;
        try {
            c.startService(new Intent(c, DrivingService.class).setAction(ACTION_CANCEL));
        } catch (IllegalStateException e) {
            // usługa właśnie się kończy
        }
    }

    // ------------------------------------------------------------------ cykl życia

    @Override
    public void onCreate() {
        super.onCreate();
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        startedAtMs = SystemClock.elapsedRealtime();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        String source = intent == null ? null : intent.getStringExtra(EXTRA_SOURCE);
        if (source == null) source = SOURCE_BLUETOOTH;
        long eventTime = intent == null ? SystemClock.elapsedRealtime()
                : intent.getLongExtra(EXTRA_EVENT_TIME, SystemClock.elapsedRealtime());

        if (ACTION_CANCEL.equals(action)) {
            EventLog.log(this, "Użytkownik: „To nie moje auto”, anulowano bez zapisu");
            finishService();
            return START_NOT_STICKY;
        }
        // Po startForegroundService() trzeba w ciągu kilku sekund pokazać powiadomienie.
        if (!goForeground(getString(ACTION_DRIVING_ENDED.equals(action)
                ? R.string.notif_saving_text : R.string.notif_driving_text))) {
            if (ACTION_DRIVING_ENDED.equals(action)) saveLastKnown(this, eventTime);
            Notifications.showTrackingBlocked(this);
            finishService();
            return START_NOT_STICKY;
        }
        running = true;

        if (ACTION_DRIVING_STARTED.equals(action)) {
            EventLog.log(this, "Usługa: start śledzenia jazdy (" + sourceName(source) + ")");
            if (!driving) {
                detector.reset();
                loggedDriving = false;
            }
            driving = true;
            waitingForFix = false;
            startGps();
            handler.removeCallbacks(watchdog);
            handler.postDelayed(watchdog, 60_000);
        } else if (ACTION_DRIVING_ENDED.equals(action)) {
            if (SOURCE_BLUETOOTH.equals(source) && driving
                    && detector.isMovingAt(eventTime, BLUETOOTH_GLITCH_WINDOW_MS)) {
                // Bluetooth zerwał się w trakcie jazdy (słaby zasięg, przełączenie telefonu): to nie parking.
                EventLog.log(this, "Rozłączenie Bluetooth w trakcie jazdy, ignoruję i śledzę dalej");
                goForeground(getString(R.string.notif_driving_text));
                return START_NOT_STICKY;
            }
            EventLog.log(this, "Usługa: koniec jazdy (" + sourceName(source) + "), ustalam miejsce parkowania");
            driving = false;
            onDrivingEnded(source, eventTime);
        } else {
            // Restart przez system bez polecenia: nie ma czego robić.
            EventLog.log(this, "Usługa uruchomiona bez polecenia (restart przez system), kończę");
            finishService();
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        stopGps();
        handler.removeCallbacksAndMessages(null);
        running = false;
        driving = false;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private boolean goForeground(String text) {
        Notification n = Notifications.driving(this, text);
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(Notifications.ID_DRIVING, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);
            } else {
                startForeground(Notifications.ID_DRIVING, n);
            }
            return true;
        } catch (RuntimeException e) {
            // brak uprawnień do lokalizacji albo system nie pozwolił na usługę w tle
            EventLog.log(this, "BŁĄD startForeground: " + e.getClass().getSimpleName() + ": " + e.getMessage());
            return false;
        }
    }

    private void finishService() {
        stopGps();
        handler.removeCallbacksAndMessages(null);
        running = false;
        driving = false;
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    // ------------------------------------------------------------------ GPS

    @SuppressLint("MissingPermission") // sprawdzane niżej
    private void startGps() {
        if (updatesRunning) return;
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            EventLog.log(this, "BŁĄD: brak uprawnienia do dokładnej lokalizacji");
            return;
        }
        try {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER,
                    GPS_INTERVAL_MS, 0f, gpsListener, Looper.getMainLooper());
            updatesRunning = true;
            EventLog.log(this, "GPS włączony");
        } catch (SecurityException | IllegalArgumentException e) {
            // brak GPS w urządzeniu albo odebrane uprawnienie
            EventLog.log(this, "BŁĄD włączania GPS: " + e);
        }
    }

    private void stopGps() {
        if (!updatesRunning) return;
        updatesRunning = false;
        locationManager.removeUpdates(gpsListener);
    }

    private final LocationListener gpsListener = new LocationListener() {
        @Override
        public void onLocationChanged(Location l) {
            detector.add(toFix(l));
            if (!loggedDriving && detector.hasDriven()) {
                loggedDriving = true;
                EventLog.log(DrivingService.this, String.format(java.util.Locale.US,
                        "GPS potwierdza jazdę (%.0f km/h)", l.getSpeed() * 3.6f));
            }
            if (waitingForFix && l.hasAccuracy() && l.getAccuracy() <= MAX_SAVE_ACCURACY_M) {
                waitingForFix = false;
                handler.removeCallbacks(waitTimeout);
                EventLog.log(DrivingService.this, String.format(java.util.Locale.US,
                        "Miejsce: nowy pomiar GPS po końcu jazdy, ±%.0f m", l.getAccuracy()));
                save(toFix(l), true);
            }
        }

        @Override
        public void onStatusChanged(String p, int s, Bundle extras) { }

        @Override
        public void onProviderEnabled(String p) { }

        @Override
        public void onProviderDisabled(String p) { }
    };

    private static ParkingDetector.Fix toFix(Location l) {
        return new ParkingDetector.Fix(l.getLatitude(), l.getLongitude(),
                l.hasAccuracy() ? l.getAccuracy() : 999f,
                l.hasSpeed() ? l.getSpeed() : Float.NaN,
                l.getElapsedRealtimeNanos() / 1_000_000L);
    }

    // ------------------------------------------------------------------ koniec jazdy

    private void onDrivingEnded(String source, long eventTime) {
        handler.removeCallbacks(watchdog);
        boolean bluetooth = SOURCE_BLUETOOTH.equals(source);

        // 1. Bluetooth: pozycja z chwili wyłączenia silnika (telefon był jeszcze w aucie).
        if (bluetooth) {
            ParkingDetector.Fix atEvent = detector.fixAt(eventTime, BLUETOOTH_FIX_MAX_GAP_MS);
            if (atEvent != null) {
                EventLog.log(this, String.format(java.util.Locale.US,
                        "Miejsce: pozycja z chwili rozłączenia Bluetooth (%d s przed), ±%.0f m",
                        (eventTime - atEvent.timeMs) / 1000, atEvent.accuracy));
                save(atEvent, false);
                return;
            }
        }

        // 2. Pierwszy postój po ostatnim odcinku jazdy.
        if (detector.hasDriven()) {
            ParkingDetector.Fix p = detector.parkingFix(), last = detector.lastFix();
            double walked = Geo.distanceMeters(p.latitude, p.longitude, last.latitude, last.longitude);
            EventLog.log(this, String.format(java.util.Locale.US,
                    "Miejsce: %s, ±%.0f m; od tego miejsca do końca jazdy przesunięcie %.0f m",
                    detector.parkingFixSource(), p.accuracy, walked));
            save(p, false);
            return;
        }
        EventLog.log(this, "Brak danych z jazdy (usługa nie śledziła jazdy)");

        // 3. Pozycja zapamiętana przez system, ale tylko z okolic zdarzenia.
        ParkingDetector.Fix cached = cachedFixNear(this, eventTime);
        if (cached != null) {
            EventLog.log(this, String.format(java.util.Locale.US,
                    "Miejsce: pozycja systemu z okolic zdarzenia (%+d s), ±%.0f m",
                    (cached.timeMs - eventTime) / 1000, cached.accuracy));
            save(cached, true);
            return;
        }

        // 4. Nowy pomiar ma sens tylko tuż po zdarzeniu (kierowca jest jeszcze przy aucie).
        long eventAge = SystemClock.elapsedRealtime() - eventTime;
        if (!bluetooth && eventAge > LATE_EVENT_MS) {
            EventLog.log(this, "BŁĄD: zdarzenie sprzed " + eventAge / 1000
                    + " s i brak pozycji z tamtej chwili; nie zapisuję zgadywanego miejsca");
            notifyFailure(this);
            finishService();
            return;
        }
        EventLog.log(this, "Czekam na aktualną pozycję GPS (do " + WAIT_FOR_FIX_MS / 1000 + " s)");
        waitingForFix = true;
        startGps();
        handler.postDelayed(waitTimeout, WAIT_FOR_FIX_MS);
    }

    private final Runnable waitTimeout = () -> {
        waitingForFix = false;
        ParkingDetector.Fix last = detector.lastFix();
        if (last != null && last.accuracy <= MAX_SAVE_ACCURACY_M) {
            EventLog.log(this, "Miejsce: ostatni (słaby) pomiar GPS po czasie oczekiwania");
            save(last, true);
        } else {
            EventLog.log(this, "BŁĄD: brak sygnału GPS, nie zapisano miejsca");
            notifyFailure(this);
            finishService();
        }
    };

    /** Co minutę: czy jazda nie skończyła się bez zgłoszenia rozłączenia (reguły w {@link DrivePolicy}). */
    private final Runnable watchdog = new Runnable() {
        @Override
        public void run() {
            long now = SystemClock.elapsedRealtime();
            boolean connected = CarBluetooth.isCarConnected(DrivingService.this);
            switch (DrivePolicy.onWatchdog(connected, now, startedAtMs, detector.lastDrivingTimeMs())) {
                case END_AND_SAVE:
                    EventLog.log(DrivingService.this, connected
                            ? "Połączono z autem, ale bez jazdy od godziny: zapisuję miejsce postoju"
                            : "Brak połączenia z autem i postój od 5 min (po zerwaniu Bluetooth): zapisuję");
                    driving = false;
                    onDrivingEnded(SOURCE_TIMEOUT, now);
                    return;
                case END_WITHOUT_SAVE:
                    EventLog.log(DrivingService.this, "Fałszywy alarm: GPS nie wykrył jazdy, kończę bez zapisu");
                    finishService();
                    return;
                default:
                    handler.postDelayed(this, 60_000);
            }
        }
    };

    /**
     * Najdokładniejsza pozycja zapamiętana przez system z okna wokół zdarzenia
     * (od {@link #CACHED_FIX_WINDOW_MS} przed do teraz). Starsze mogą pochodzić z trasy.
     */
    @SuppressLint("MissingPermission")
    static ParkingDetector.Fix cachedFixNear(Context c, long eventTimeMs) {
        if (c.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) return null;
        LocationManager lm = (LocationManager) c.getSystemService(Context.LOCATION_SERVICE);
        Location best = null;
        for (String p : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER,
                LocationManager.PASSIVE_PROVIDER}) {
            try {
                Location l = lm.getLastKnownLocation(p);
                if (l == null || !l.hasAccuracy() || l.getAccuracy() > MAX_SAVE_ACCURACY_M) continue;
                long t = l.getElapsedRealtimeNanos() / 1_000_000L;
                if (t < eventTimeMs - CACHED_FIX_WINDOW_MS) continue;
                if (best == null || l.getAccuracy() < best.getAccuracy()) best = l;
            } catch (SecurityException | IllegalArgumentException e) {
                // pomijamy to źródło
            }
        }
        return best == null ? null : toFix(best);
    }

    static void notifyFailure(Context c) {
        Notifications.showParked(c, c.getString(R.string.notif_parked_failed));
    }

    private static String sourceName(String source) {
        return SOURCE_BLUETOOTH.equals(source) ? "Bluetooth auta" : "brak jazdy (reguła czasu)";
    }

    private void save(ParkingDetector.Fix fix, boolean approximate) {
        saveParking(this, fix, approximate);
        finishService();
    }

    /** Zapisuje miejsce i pokazuje powiadomienie. Używane też przez odbiornik, gdy usługa nie mogła wystartować. */
    static void saveParking(Context c, ParkingDetector.Fix fix, boolean approximate) {
        // Fix.timeMs jest w czasie od uruchomienia telefonu; przeliczamy na zwykły zegar.
        long wallTime = System.currentTimeMillis() - (SystemClock.elapsedRealtime() - fix.timeMs);
        String note = c.getString(approximate ? R.string.auto_note_approx : R.string.auto_note);
        ParkingStore.Spot spot = new ParkingStore.Spot(fix.latitude, fix.longitude,
                fix.accuracy, wallTime, note);
        new ParkingStore(c).save(spot);
        EventLog.log(c, String.format(java.util.Locale.US, "ZAPISANO parking: %.6f, %.6f%s",
                fix.latitude, fix.longitude, approximate ? " (przybliżony)" : ""));
        Notifications.showParked(c, c.getString(approximate
                ? R.string.notif_parked_text_approx : R.string.notif_parked_text));
        AddressLookup.lookupAsync(c, spot, true);
    }

    /**
     * Awaryjnie, gdy usługa nie mogła wystartować: pozycja zapamiętana przez system,
     * ale tylko z okolic zdarzenia. Jeśli jej brak, użytkownik dostaje powiadomienie,
     * żeby zapisał miejsce ręcznie (lepsze niż zapis miejsca z trasy).
     */
    static void saveLastKnown(Context c, long eventTimeMs) {
        ParkingDetector.Fix f = cachedFixNear(c, eventTimeMs);
        if (f == null) {
            EventLog.log(c, "Zapis awaryjny: brak pozycji z okolic zdarzenia, proszę o ręczny zapis");
            notifyFailure(c);
            return;
        }
        EventLog.log(c, String.format(java.util.Locale.US, "Zapis awaryjny: pozycja %+d s od zdarzenia, ±%.0f m",
                (f.timeMs - eventTimeMs) / 1000, f.accuracy));
        saveParking(c, f, true);
    }
}
