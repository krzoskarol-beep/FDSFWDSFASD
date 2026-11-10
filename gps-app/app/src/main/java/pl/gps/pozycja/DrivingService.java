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
 * miejsce parkowania. Startuje ją {@link TransitionReceiver}, gdy usługi Google
 * wykryją jazdę samochodem, i zatrzymuje, gdy wykryją jej koniec.
 * GPS jest włączony tylko w trakcie jazdy.
 */
public class DrivingService extends Service {

    static final String ACTION_DRIVING_STARTED = "pl.gps.pozycja.DRIVING_STARTED";
    static final String ACTION_DRIVING_ENDED = "pl.gps.pozycja.DRIVING_ENDED";
    static final String ACTION_CANCEL = "pl.gps.pozycja.DRIVING_CANCEL";

    private static final long GPS_INTERVAL_MS = 2000;
    /** Jeśli przez tyle czasu nie było jazdy, uznajemy, że auto stoi (gdyby system nie zgłosił końca). */
    private static final long NO_DRIVING_TIMEOUT_MS = 20 * 60_000L;
    /** Po zgłoszeniu końca jazdy bez danych z jazdy czekamy tyle na aktualną pozycję. */
    private static final long WAIT_FOR_FIX_MS = 45_000;
    /** Ostatnia znana pozycja z systemu jest użyteczna, jeśli jest młodsza niż to. */
    private static final long LAST_KNOWN_MAX_AGE_MS = 5 * 60_000L;
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
    static boolean start(Context c, String action) {
        Intent i = new Intent(c, DrivingService.class).setAction(action);
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

        if (ACTION_CANCEL.equals(action)) {
            EventLog.log(this, "Użytkownik: „To nie moje auto”, anulowano bez zapisu");
            finishService();
            return START_NOT_STICKY;
        }
        // Po startForegroundService() trzeba w ciągu kilku sekund pokazać powiadomienie.
        if (!goForeground(getString(ACTION_DRIVING_ENDED.equals(action)
                ? R.string.notif_saving_text : R.string.notif_driving_text))) {
            if (ACTION_DRIVING_ENDED.equals(action)) saveLastKnown(this);
            finishService();
            return START_NOT_STICKY;
        }
        running = true;

        if (ACTION_DRIVING_STARTED.equals(action)) {
            EventLog.log(this, "Usługa: start śledzenia jazdy");
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
            EventLog.log(this, "Usługa: koniec jazdy, ustalam miejsce parkowania");
            driving = false;
            onDrivingEnded();
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

    private void onDrivingEnded() {
        handler.removeCallbacks(watchdog);
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
        // Brak danych z jazdy (np. usługa nie działała w trakcie jazdy): weź świeżą pozycję.
        ParkingDetector.Fix recent = freshLastKnown();
        if (recent != null) {
            EventLog.log(this, String.format(java.util.Locale.US,
                    "Miejsce: ostatnia znana pozycja systemu, ±%.0f m", recent.accuracy));
            save(recent, true);
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
            Notifications.showParked(this, getString(R.string.notif_parked_failed));
            finishService();
        }
    };

    /** Co minutę: czy jazda nie skończyła się bez zgłoszenia z systemu. */
    private final Runnable watchdog = new Runnable() {
        @Override
        public void run() {
            long now = SystemClock.elapsedRealtime();
            long lastDriving = detector.lastDrivingTimeMs();
            if (lastDriving >= 0 && now - lastDriving > NO_DRIVING_TIMEOUT_MS) {
                EventLog.log(DrivingService.this, "Brak jazdy od 20 min, a system nie zgłosił końca: zapisuję");
                driving = false;
                onDrivingEnded();
                return;
            }
            if (lastDriving < 0 && now - startedAtMs > NO_DRIVING_TIMEOUT_MS) {
                // Fałszywy alarm (np. chodzenie po mieście): nic nie zapisujemy.
                EventLog.log(DrivingService.this, "Fałszywy alarm: przez 20 min GPS nie wykrył jazdy, kończę bez zapisu");
                finishService();
                return;
            }
            handler.postDelayed(this, 60_000);
        }
    };

    @SuppressLint("MissingPermission")
    private ParkingDetector.Fix freshLastKnown() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) return null;
        Location best = null;
        for (String p : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER,
                LocationManager.PASSIVE_PROVIDER}) {
            try {
                Location l = locationManager.getLastKnownLocation(p);
                if (l == null || !l.hasAccuracy() || l.getAccuracy() > MAX_SAVE_ACCURACY_M) continue;
                long age = (SystemClock.elapsedRealtimeNanos() - l.getElapsedRealtimeNanos()) / 1_000_000L;
                if (age > LAST_KNOWN_MAX_AGE_MS) continue;
                if (best == null || l.getAccuracy() < best.getAccuracy()) best = l;
            } catch (SecurityException | IllegalArgumentException e) {
                // pomijamy to źródło
            }
        }
        return best == null ? null : toFix(best);
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
        new ParkingStore(c).save(new ParkingStore.Spot(fix.latitude, fix.longitude,
                fix.accuracy, wallTime, note));
        EventLog.log(c, String.format(java.util.Locale.US, "ZAPISANO parking: %.6f, %.6f%s",
                fix.latitude, fix.longitude, approximate ? " (przybliżony)" : ""));
        Notifications.showParked(c, c.getString(approximate
                ? R.string.notif_parked_text_approx : R.string.notif_parked_text));
    }

    @SuppressLint("MissingPermission")
    /** Awaryjnie: zapis ostatniej znanej pozycji, gdy usługa nie mogła działać. */
    static void saveLastKnown(Context c) {
        if (c.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) return;
        LocationManager lm = (LocationManager) c.getSystemService(Context.LOCATION_SERVICE);
        Location best = null;
        for (String p : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER,
                LocationManager.PASSIVE_PROVIDER}) {
            try {
                Location l = lm.getLastKnownLocation(p);
                if (l != null && (best == null || l.getElapsedRealtimeNanos() > best.getElapsedRealtimeNanos())) {
                    best = l;
                }
            } catch (SecurityException | IllegalArgumentException e) {
                // pomijamy to źródło
            }
        }
        if (best == null) {
            EventLog.log(c, "Zapis awaryjny: system nie zna żadnej pozycji");
            return;
        }
        long ageMs = (SystemClock.elapsedRealtimeNanos() - best.getElapsedRealtimeNanos()) / 1_000_000L;
        if (ageMs > 10 * 60_000L) {
            EventLog.log(c, "Zapis awaryjny: ostatnia pozycja jest za stara (" + ageMs / 60_000 + " min)");
            return;
        }
        EventLog.log(c, String.format(java.util.Locale.US, "Zapis awaryjny: pozycja sprzed %d s, ±%.0f m",
                ageMs / 1000, best.hasAccuracy() ? best.getAccuracy() : -1f));
        saveParking(c, new ParkingDetector.Fix(best.getLatitude(), best.getLongitude(),
                best.hasAccuracy() ? best.getAccuracy() : 0f, Float.NaN,
                best.getElapsedRealtimeNanos() / 1_000_000L), true);
    }
}
