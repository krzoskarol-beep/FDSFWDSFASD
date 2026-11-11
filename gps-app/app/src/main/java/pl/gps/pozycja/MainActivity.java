package pl.gps.pozycja;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Insets;
import android.hardware.GeomagneticField;
import android.location.GnssStatus;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.provider.Settings;
import android.text.InputType;
import android.text.format.DateUtils;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Pokazuje aktualną pozycję GPS telefonu.
 * Korzysta wyłącznie z systemowego LocationManager (bez Google Play Services),
 * więc działa także na telefonach bez usług Google.
 */
public class MainActivity extends Activity {

    private static final int REQ_LOCATION = 1;
    private static final long MIN_UPDATE_MS = 1000;
    /** Pozycja młodsza niż tyle jest uznawana za „aktualną”. */
    private static final long FRESH_MS = 10_000;
    /** Nowsza pozycja wygrywa ze starszą, jeśli różnica czasu jest większa niż to. */
    private static final long SIGNIFICANTLY_NEWER_MS = 10_000;

    private LocationManager locationManager;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private Location best;
    private boolean updatesRunning;
    private boolean permissionDeniedForever;
    private int satellitesUsed = -1;
    private int satellitesVisible = -1;

    private TextView status, latitude, longitude, latitudeDms, longitudeDms;
    private TextView accuracy, altitude, speed, bearing, satellites, provider, fixTime;
    private Button actionButton;

    // --- Gdzie zaparkowałem?
    /** Akcja skrótu na ikonie aplikacji (res/xml/shortcuts.xml). */
    static final String ACTION_SAVE_PARKING = "pl.gps.pozycja.SAVE_PARKING";
    /** Pozycja starsza niż tyle jest przy zapisie oznaczana jako nieaktualna. */
    private static final long SAVE_STALE_MS = 30_000;
    /** Powyżej tej niedokładności ostrzegamy przy zapisie. */
    private static final float SAVE_LOW_ACCURACY_M = 50f;

    private ParkingStore parkingStore;
    private ParkingStore.Spot spot;
    private Compass compass;
    /** Azymut z kompasu względem północy magnetycznej; null, dopóki brak odczytu. */
    private Float compassAzimuth;
    private boolean compassNeedsCalibration;
    /** Deklinacja magnetyczna: różnica między północą magnetyczną a geograficzną. */
    private float declination;
    /** Zapis zlecony (np. ze skrótu), zanim była aktualna pozycja. */
    private boolean pendingSave;
    private AlertDialog openDialog;

    private View parkingEmpty, parkingSaved;
    private ArrowView parkingArrow;
    private TextView parkingDistance, parkingDirection, parkingCompassHint;
    private TextView parkingNote, parkingSavedAt, parkingSavedAccuracy, parkingAddress;

    // --- Automatyczne zapisywanie parkowania
    /** Akcja z powiadomienia „Zapisano miejsce parkowania” → „Prowadź”. */
    static final String ACTION_NAVIGATE_TO_CAR = "pl.gps.pozycja.NAVIGATE_TO_CAR";
    private static final int REQ_AUTO_LOCATION = 2;
    private static final int REQ_AUTO_FOREGROUND = 3;
    private static final int REQ_AUTO_BACKGROUND = 4;
    private static final int REQ_BT_PICK = 5;
    private static final int REQ_BATTERY = 6;

    private Switch autoSwitch;
    private TextView autoStatus, autoBatteryHint;
    private Button autoBatteryButton;
    private TextView autoBtDevices;
    /** Zapobiega reakcji na programowe przestawienie przełącznika. */
    private boolean suppressSwitch;
    private boolean notificationsAsked;
    /** Prośba o wyłączenie optymalizacji baterii padła w tej konfiguracji (nie pytamy w kółko). */
    private boolean batteryAsked;
    /** Konfiguracja trwa od włączenia przełącznika do zapisania ustawienia (okna uprawnień). */
    private boolean autoSetupInProgress;

    /** Usługa w tle zapisała nowe miejsce: odśwież kartę „Mój samochód”. */
    private final SharedPreferences.OnSharedPreferenceChangeListener parkingChanged = (p, key) -> {
        spot = parkingStore.load();
        showParking();
    };

    // ------------------------------------------------------------------ cykl życia

    @Override
    protected void attachBaseContext(Context base) {
        // Motyw wybrany w aplikacji (systemowy / jasny / ciemny), patrz ThemePrefs.
        super.attachBaseContext(ThemePrefs.wrap(base));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);

        status = findViewById(R.id.status);
        latitude = findViewById(R.id.latitude);
        longitude = findViewById(R.id.longitude);
        latitudeDms = findViewById(R.id.latitudeDms);
        longitudeDms = findViewById(R.id.longitudeDms);
        accuracy = findViewById(R.id.accuracy);
        altitude = findViewById(R.id.altitude);
        speed = findViewById(R.id.speed);
        bearing = findViewById(R.id.bearing);
        satellites = findViewById(R.id.satellites);
        provider = findViewById(R.id.provider);
        fixTime = findViewById(R.id.fixTime);
        actionButton = findViewById(R.id.actionButton);

        findViewById(R.id.btnMaps).setOnClickListener(v -> openInMaps());
        findViewById(R.id.btnCopy).setOnClickListener(v -> copyCoordinates());
        findViewById(R.id.btnShare).setOnClickListener(v -> shareCoordinates());
        setupThemeChooser();
        findViewById(R.id.btnHistory).setOnClickListener(
                v -> startActivity(new Intent(this, HistoryActivity.class)));
        findViewById(R.id.btnDiagnostics).setOnClickListener(
                v -> startActivity(new Intent(this, DiagnosticsActivity.class)));

        parkingEmpty = findViewById(R.id.parkingEmpty);
        parkingSaved = findViewById(R.id.parkingSaved);
        parkingArrow = findViewById(R.id.parkingArrow);
        parkingDistance = findViewById(R.id.parkingDistance);
        parkingDirection = findViewById(R.id.parkingDirection);
        parkingCompassHint = findViewById(R.id.parkingCompassHint);
        parkingNote = findViewById(R.id.parkingNote);
        parkingAddress = findViewById(R.id.parkingAddress);
        parkingSavedAt = findViewById(R.id.parkingSavedAt);
        parkingSavedAccuracy = findViewById(R.id.parkingSavedAccuracy);

        findViewById(R.id.btnSaveParking).setOnClickListener(v -> showSaveParkingDialog());
        findViewById(R.id.btnSaveHere).setOnClickListener(v -> showSaveParkingDialog());
        findViewById(R.id.btnNavigate).setOnClickListener(v -> navigateToCar());
        findViewById(R.id.btnDeleteParking).setOnClickListener(v -> confirmDeleteParking());

        parkingStore = new ParkingStore(this);
        spot = parkingStore.load();
        compass = new Compass(this, new Compass.Listener() {
            @Override
            public void onAzimuthChanged(float azimuthDegrees) {
                compassAzimuth = azimuthDegrees;
                updateParkingDirection();
            }

            @Override
            public void onCalibrationChanged(boolean needsCalibration) {
                compassNeedsCalibration = needsCalibration;
                updateParkingDirection();
            }
        });

        autoSwitch = findViewById(R.id.autoSwitch);
        autoStatus = findViewById(R.id.autoStatus);
        autoBatteryHint = findViewById(R.id.autoBatteryHint);
        autoBatteryButton = findViewById(R.id.autoBatteryButton);
        autoSwitch.setOnCheckedChangeListener((b, checked) -> {
            if (!suppressSwitch) onAutoSwitchChanged(checked);
        });
        autoBatteryButton.setOnClickListener(v -> requestIgnoreBatteryOptimizations());
        autoBtDevices = findViewById(R.id.autoBtDevices);
        findViewById(R.id.autoBtChoose).setOnClickListener(v -> chooseCarBluetooth());
        Notifications.createChannels(this);

        applySystemBarInsets(findViewById(R.id.root));

        if (savedInstanceState == null) {
            handleIntent(getIntent());
        } else {
            pendingSave = savedInstanceState.getBoolean(STATE_PENDING_SAVE, false);
        }
        if (!hasAnyLocationPermission()) {
            requestLocationPermission();
        }
    }

    private static final String STATE_PENDING_SAVE = "pendingSave";

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        // Zapis ze skrótu czeka na pozycję: nie zgub go przy obrocie ekranu.
        outState.putBoolean(STATE_PENDING_SAVE, pendingSave);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private void handleIntent(Intent intent) {
        if (intent != null && ACTION_SAVE_PARKING.equals(intent.getAction())) {
            // Ze skrótu: zapisz, gdy tylko będzie aktualna pozycja.
            pendingSave = true;
            Toast.makeText(this, R.string.parking_waiting_for_fix, Toast.LENGTH_SHORT).show();
        } else if (intent != null && ACTION_NAVIGATE_TO_CAR.equals(intent.getAction())) {
            spot = parkingStore.load();
            navigateToCar();
        }
    }

    @Override
    protected void onDestroy() {
        if (openDialog != null) openDialog.dismiss();
        super.onDestroy();
    }

    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter(LocationManager.PROVIDERS_CHANGED_ACTION);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(providersChanged, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(providersChanged, filter);
        }
        refreshState();
        spot = parkingStore.load();
        parkingStore.addListener(parkingChanged);
        showParking();
        updateAutoUi();
        handler.post(ticker);
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(providersChanged);
        handler.removeCallbacks(ticker);
        stopUpdates();
        compass.stop();
        parkingStore.removeListener(parkingChanged);
    }

    // ------------------------------------------------------------------ uprawnienia

    private boolean hasFinePermission() {
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }

    private boolean hasAnyLocationPermission() {
        return hasFinePermission()
                || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }

    private void requestLocationPermission() {
        requestPermissions(new String[]{
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
        }, REQ_LOCATION);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQ_BT_PICK) {
            if (CarBluetooth.hasPermission(this)) chooseCarBluetooth();
            else autoSetupFailed(R.string.bt_permission_denied);
            return;
        }
        if (requestCode == REQ_AUTO_LOCATION || requestCode == REQ_AUTO_FOREGROUND
                || requestCode == REQ_AUTO_BACKGROUND) {
            onAutoPermissionResult(requestCode);
            return;
        }
        if (requestCode != REQ_LOCATION) return;
        // Jeśli użytkownik odmówił, a system nie pozwala już pokazać okna, to odmowa jest trwała.
        permissionDeniedForever = !hasAnyLocationPermission()
                && !shouldShowRequestPermissionRationale(Manifest.permission.ACCESS_FINE_LOCATION);
        refreshState();
    }

    // ------------------------------------------------------------------ stan aplikacji

    private boolean isLocationEnabled() {
        if (Build.VERSION.SDK_INT >= 28) {
            return locationManager.isLocationEnabled();
        }
        return locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)
                || locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER);
    }

    /** Ustala, czy można śledzić pozycję, i odpowiednio uruchamia lub zatrzymuje pomiary. */
    private void refreshState() {
        if (!hasAnyLocationPermission()) {
            stopUpdates();
            if (permissionDeniedForever) {
                showProblem(R.string.status_permission_denied_forever, R.string.grant_permission,
                        v -> openAppSettings());
            } else {
                showProblem(R.string.status_no_permission, R.string.grant_permission,
                        v -> requestLocationPermission());
            }
            return;
        }
        permissionDeniedForever = false;

        if (!isLocationEnabled()) {
            stopUpdates();
            showProblem(R.string.status_disabled, R.string.open_settings,
                    v -> startActivitySafe(new Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS)));
            return;
        }

        actionButton.setVisibility(View.GONE);
        startUpdates();
        updateStatus();
    }

    private void showProblem(int messageRes, int buttonRes, View.OnClickListener action) {
        status.setText(messageRes);
        status.setTextColor(getColor(R.color.error));
        actionButton.setText(buttonRes);
        actionButton.setOnClickListener(action);
        actionButton.setVisibility(View.VISIBLE);
    }

    // ------------------------------------------------------------------ pomiary

    @SuppressWarnings("MissingPermission") // sprawdzane w refreshState()
    private void startUpdates() {
        if (updatesRunning) return;
        updatesRunning = true;

        for (String p : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER}) {
            if (!locationManager.getAllProviders().contains(p)) continue;
            try {
                Location last = locationManager.getLastKnownLocation(p);
                if (last != null && isBetter(last, best)) best = last;
                locationManager.requestLocationUpdates(p, MIN_UPDATE_MS, 0f, listener,
                        Looper.getMainLooper());
            } catch (SecurityException | IllegalArgumentException e) {
                // np. GPS wymaga dokładnej lokalizacji, a użytkownik dał tylko przybliżoną
            }
        }

        if (hasFinePermission()) {
            try {
                locationManager.registerGnssStatusCallback(gnssCallback, handler);
            } catch (SecurityException e) {
                // brak informacji o satelitach, pozycja nadal działa
            }
        }
        showLocation();
    }

    private void stopUpdates() {
        if (!updatesRunning) return;
        updatesRunning = false;
        locationManager.removeUpdates(listener);
        locationManager.unregisterGnssStatusCallback(gnssCallback);
        satellitesUsed = satellitesVisible = -1;
    }

    private final LocationListener listener = new LocationListener() {
        @Override
        public void onLocationChanged(Location location) {
            if (isBetter(location, best)) {
                best = location;
                showLocation();
                updateStatus();
            }
        }

        // Metody poniżej są abstrakcyjne na Androidzie < 11, więc muszą być zaimplementowane.
        @Override
        public void onStatusChanged(String p, int s, Bundle extras) { }

        @Override
        public void onProviderEnabled(String p) { refreshState(); }

        @Override
        public void onProviderDisabled(String p) { refreshState(); }
    };

    private final GnssStatus.Callback gnssCallback = new GnssStatus.Callback() {
        @Override
        public void onSatelliteStatusChanged(GnssStatus gnss) {
            int used = 0;
            for (int i = 0; i < gnss.getSatelliteCount(); i++) {
                if (gnss.usedInFix(i)) used++;
            }
            satellitesUsed = used;
            satellitesVisible = gnss.getSatelliteCount();
            satellites.setText(String.format(Locale.getDefault(), "%d / %d",
                    satellitesUsed, satellitesVisible));
        }
    };

    private final BroadcastReceiver providersChanged = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            refreshState();
        }
    };

    /** Odświeża co sekundę wiek pomiaru, żeby było widać, czy pozycja jest świeża. */
    private final Runnable ticker = new Runnable() {
        @Override
        public void run() {
            if (updatesRunning) {
                updateStatus();
                updateFixTime();
            }
            updateParkingSavedAt();
            updateAutoUi();
            handler.postDelayed(this, 1000);
        }
    };

    /** Wybiera lepszą z dwóch pozycji: wyraźnie nowszą, a przy podobnym czasie dokładniejszą. */
    private static boolean isBetter(Location candidate, Location current) {
        if (current == null) return true;
        long delta = ageMs(current) - ageMs(candidate); // > 0: kandydat jest nowszy
        if (delta > SIGNIFICANTLY_NEWER_MS) return true;
        if (delta < -SIGNIFICANTLY_NEWER_MS) return false;

        float accDelta = candidate.getAccuracy() - current.getAccuracy();
        if (accDelta < 0) return true;                       // dokładniejsza
        if (delta > 0 && accDelta <= 0) return true;         // nowsza i nie gorsza
        boolean sameProvider = candidate.getProvider() != null
                && candidate.getProvider().equals(current.getProvider());
        return delta > 0 && accDelta <= 200 && sameProvider; // nowsza z tego samego źródła
    }

    private static long ageMs(Location l) {
        return (SystemClock.elapsedRealtimeNanos() - l.getElapsedRealtimeNanos()) / 1_000_000L;
    }

    // ------------------------------------------------------------------ wyświetlanie

    private void updateStatus() {
        if (!updatesRunning) return;
        String coarseNote = hasFinePermission() ? "" : "\n" + getString(R.string.status_coarse_only);

        if (best == null) {
            status.setText(getString(R.string.status_waiting) + coarseNote);
            status.setTextColor(getColor(R.color.warn));
        } else if (ageMs(best) <= FRESH_MS) {
            status.setText(getString(R.string.status_ok) + coarseNote);
            status.setTextColor(getColor(R.color.ok));
        } else {
            status.setText(getString(R.string.status_stale, Formatters.formatAge(ageMs(best))) + coarseNote);
            status.setTextColor(getColor(R.color.warn));
        }
    }

    private void showLocation() {
        if (best == null) return;
        Location l = best;

        latitude.setText(String.format(Locale.US, "%.6f°", l.getLatitude()));
        longitude.setText(String.format(Locale.US, "%.6f°", l.getLongitude()));
        latitudeDms.setText(Formatters.toDms(l.getLatitude(), true));
        longitudeDms.setText(Formatters.toDms(l.getLongitude(), false));

        accuracy.setText(l.hasAccuracy()
                ? String.format(Locale.getDefault(), "± %.0f m", l.getAccuracy()) : "—");

        if (Build.VERSION.SDK_INT >= 34 && l.hasMslAltitude()) {
            altitude.setText(String.format(Locale.getDefault(), "%.0f m n.p.m.", l.getMslAltitudeMeters()));
        } else if (l.hasAltitude()) {
            altitude.setText(String.format(Locale.getDefault(), "≈ %.0f m", l.getAltitude()));
        } else {
            altitude.setText("—");
        }

        speed.setText(l.hasSpeed()
                ? String.format(Locale.getDefault(), "%.1f km/h", l.getSpeed() * 3.6f) : "—");

        // Kierunek ma sens tylko w ruchu (powyżej ok. 2 km/h).
        if (l.hasBearing() && l.hasSpeed() && l.getSpeed() > 0.5f) {
            bearing.setText(String.format(Locale.getDefault(), "%.0f° (%s)",
                    l.getBearing(), Formatters.compassDirection(l.getBearing())));
        } else {
            bearing.setText("—");
        }

        if (satellitesVisible < 0) satellites.setText("—");
        provider.setText(providerName(l.getProvider()));
        updateFixTime();

        declination = new GeomagneticField((float) l.getLatitude(), (float) l.getLongitude(),
                (float) l.getAltitude(), System.currentTimeMillis()).getDeclination();
        updateParkingDirection();
        checkPendingSave();
    }

    private void updateFixTime() {
        if (best == null) return;
        String clock = DateFormat.getTimeInstance(DateFormat.MEDIUM).format(new Date(best.getTime()));
        fixTime.setText(clock + "  (" + Formatters.formatAge(ageMs(best)) + " temu)");
    }

    private static String providerName(String p) {
        if (LocationManager.GPS_PROVIDER.equals(p)) return "GPS (satelity)";
        if (LocationManager.NETWORK_PROVIDER.equals(p)) return "Sieć (Wi‑Fi / BTS)";
        if ("fused".equals(p)) return "Połączone (GPS + sieć)";
        return p == null ? "—" : p;
    }

    // ------------------------------------------------------------------ gdzie zaparkowałem?

    /** Pokazuje kartę „Mój samochód” zgodnie z tym, czy miejsce jest zapisane. */
    private void showParking() {
        boolean saved = spot != null;
        parkingEmpty.setVisibility(saved ? View.GONE : View.VISIBLE);
        parkingSaved.setVisibility(saved ? View.VISIBLE : View.GONE);
        if (!saved) {
            compass.stop();
            return;
        }
        compass.start();

        parkingAddress.setText(spot.address);
        parkingAddress.setVisibility(spot.address.isEmpty() ? View.GONE : View.VISIBLE);
        parkingNote.setText(spot.note);
        parkingNote.setVisibility(spot.note.isEmpty() ? View.GONE : View.VISIBLE);
        parkingSavedAccuracy.setText(spot.accuracy > 0
                ? getString(R.string.parking_saved_accuracy, Math.round(spot.accuracy)) : "");
        updateParkingSavedAt();
        updateParkingDirection();
    }

    private void updateParkingSavedAt() {
        if (spot == null) return;
        Date when = new Date(spot.savedAt);
        String clock = DateUtils.isToday(spot.savedAt)
                ? "o " + DateFormat.getTimeInstance(DateFormat.SHORT).format(when)
                : DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(when);
        long age = System.currentTimeMillis() - spot.savedAt;
        parkingSavedAt.setText(getString(R.string.parking_saved_at, clock, Formatters.formatAge(age)));
    }

    /** Odległość, kierunek i strzałka do auta. Wołane przy każdej nowej pozycji i odczycie kompasu. */
    private void updateParkingDirection() {
        if (spot == null) return;

        if (!compass.isAvailable()) {
            parkingCompassHint.setText(R.string.parking_hint_no_compass);
            parkingCompassHint.setTextColor(getColor(R.color.text_secondary));
        } else if (compassNeedsCalibration) {
            parkingCompassHint.setText(R.string.parking_hint_calibrate);
            parkingCompassHint.setTextColor(getColor(R.color.warn));
        } else {
            parkingCompassHint.setText(R.string.parking_hint_compass);
            parkingCompassHint.setTextColor(getColor(R.color.text_secondary));
        }

        if (best == null) {
            parkingDistance.setText("—");
            parkingDirection.setText(R.string.parking_waiting_position);
            setArrowDescription(getString(R.string.parking_waiting_position));
            parkingArrow.setArrived(false);
            parkingArrow.hideArrow();
            return;
        }

        double lat = best.getLatitude(), lon = best.getLongitude();
        double distance = Geo.distanceMeters(lat, lon, spot.latitude, spot.longitude);
        double bearingToCar = Geo.bearingDegrees(lat, lon, spot.latitude, spot.longitude);
        parkingDistance.setText(Formatters.formatDistance(distance));

        // „Na miejscu”, gdy auto jest bliżej niż dokładność GPS (ale 10–30 m).
        float arriveRadius = Math.max(10f, Math.min(30f, best.hasAccuracy() ? best.getAccuracy() : 30f));
        if (distance <= arriveRadius) {
            parkingDirection.setText(R.string.parking_arrived);
            parkingArrow.setArrived(true);
            setArrowDescription(getString(R.string.parking_arrived));
            return;
        }
        parkingArrow.setArrived(false);
        String absolute = getString(R.string.parking_direction,
                Formatters.compassDirection((float) bearingToCar), Math.round(bearingToCar) % 360);
        String distanceText = Formatters.formatDistance(distance);

        if (compassAzimuth != null) {
            // Kompas wskazuje północ magnetyczną, a kierunek do auta liczymy od geograficznej.
            float heading = compassAzimuth + declination;
            float angle = (float) Geo.normalizeDegrees(bearingToCar - heading);
            parkingArrow.setAngle(angle);
            String relative = Formatters.relativeDirection(angle);
            parkingDirection.setText(getString(R.string.parking_direction_relative, absolute, relative));
            setArrowDescription(getString(R.string.parking_arrow_description, distanceText, relative));
        } else {
            parkingArrow.setAngle((float) bearingToCar); // góra ekranu = północ
            parkingDirection.setText(absolute);
            setArrowDescription(getString(R.string.parking_arrow_description, distanceText, absolute));
        }
    }

    /** Opis strzałki dla TalkBack; zmieniamy go tylko, gdy treść się zmieni (kompas odświeża się często). */
    private void setArrowDescription(String text) {
        if (!text.contentEquals(parkingArrow.getContentDescription() == null ? "" : parkingArrow.getContentDescription())) {
            parkingArrow.setContentDescription(text);
        }
    }

    private void checkPendingSave() {
        if (pendingSave && best != null && ageMs(best) <= FRESH_MS
                && (openDialog == null || !openDialog.isShowing())) {
            pendingSave = false;
            showSaveParkingDialog();
        }
    }

    private void showSaveParkingDialog() {
        if (best == null) {
            pendingSave = true;
            Toast.makeText(this, R.string.parking_waiting_for_fix, Toast.LENGTH_SHORT).show();
            return;
        }

        StringBuilder msg = new StringBuilder();
        if (spot != null) msg.append(getString(R.string.parking_dialog_replace));
        long age = ageMs(best);
        if (age > SAVE_STALE_MS) {
            if (msg.length() > 0) msg.append("\n\n");
            msg.append(getString(R.string.parking_dialog_stale, Formatters.formatAge(age)));
        }
        if (best.hasAccuracy() && best.getAccuracy() > SAVE_LOW_ACCURACY_M) {
            if (msg.length() > 0) msg.append("\n\n");
            msg.append(getString(R.string.parking_dialog_low_accuracy, Math.round(best.getAccuracy())));
        }

        EditText note = new EditText(this);
        note.setHint(R.string.parking_dialog_note_hint);
        note.setSingleLine(true);
        note.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        FrameLayout box = new FrameLayout(this);
        int pad = Math.round(24 * getResources().getDisplayMetrics().density);
        box.setPadding(pad, pad / 3, pad, 0);
        box.addView(note);

        AlertDialog.Builder b = new AlertDialog.Builder(this)
                .setTitle(R.string.parking_dialog_title)
                .setView(box)
                .setPositiveButton(R.string.parking_dialog_save,
                        (d, w) -> saveParking(note.getText().toString().trim()))
                .setNegativeButton(R.string.parking_dialog_cancel, null);
        if (msg.length() > 0) b.setMessage(msg);
        openDialog = b.show();
    }

    private void saveParking(String note) {
        if (best == null) return;
        // Zapisujemy najnowszą pozycję z chwili naciśnięcia „Zapisz”.
        spot = new ParkingStore.Spot(best.getLatitude(), best.getLongitude(),
                best.hasAccuracy() ? best.getAccuracy() : 0f, System.currentTimeMillis(), note);
        parkingStore.save(spot);
        AddressLookup.lookupAsync(this, spot, false);
        EventLog.log(this, String.format(Locale.US, "Ręczny zapis parkingu, ±%.0f m", spot.accuracy));
        Toast.makeText(this, R.string.parking_saved_toast, Toast.LENGTH_SHORT).show();
        showParking();
    }

    private void confirmDeleteParking() {
        openDialog = new AlertDialog.Builder(this)
                .setTitle(R.string.parking_delete_title)
                .setPositiveButton(R.string.parking_delete, (d, w) -> {
                    parkingStore.clear();
                    EventLog.log(this, "Usunięto zapisane miejsce parkowania");
                    spot = null;
                    compassAzimuth = null;
                    showParking();
                })
                .setNegativeButton(R.string.parking_dialog_cancel, null)
                .show();
    }

    /** Nawigacja piesza do auta: Mapy Google, potem dowolna aplikacja map, potem przeglądarka. */
    private void navigateToCar() {
        if (spot == null) return;
        String c = String.format(Locale.US, "%.6f,%.6f", spot.latitude, spot.longitude);
        Intent nav = new Intent(Intent.ACTION_VIEW, Uri.parse("google.navigation:q=" + c + "&mode=w"))
                .setPackage("com.google.android.apps.maps");
        if (startActivitySafe(nav)) return;

        Uri geo = Uri.parse("geo:" + c + "?q=" + c + "(" + Uri.encode(getString(R.string.parking_label)) + ")");
        if (startActivitySafe(new Intent(Intent.ACTION_VIEW, geo))) return;

        Uri web = Uri.parse("https://www.google.com/maps/dir/?api=1&travelmode=walking&destination=" + c);
        if (!startActivitySafe(new Intent(Intent.ACTION_VIEW, web))) {
            Toast.makeText(this, R.string.no_maps_app, Toast.LENGTH_SHORT).show();
        }
    }

    // ------------------------------------------------------------------ wygląd

    private void setupThemeChooser() {
        android.widget.RadioGroup group = findViewById(R.id.themeGroup);
        int mode = ThemePrefs.get(this);
        group.check(mode == ThemePrefs.MODE_DARK ? R.id.themeDark
                : mode == ThemePrefs.MODE_LIGHT ? R.id.themeLight : R.id.themeSystem);
        group.setOnCheckedChangeListener((g, id) -> {
            int chosen = id == R.id.themeDark ? ThemePrefs.MODE_DARK
                    : id == R.id.themeLight ? ThemePrefs.MODE_LIGHT : ThemePrefs.MODE_SYSTEM;
            if (chosen == ThemePrefs.get(this)) return;
            ThemePrefs.set(this, chosen);
            recreate(); // wczytaj ekran od nowa z nowymi kolorami
        });
    }

    // ------------------------------------------------------------------ automatyczne zapisywanie

    private void onAutoSwitchChanged(boolean checked) {
        if (!checked) {
            AutoParking.disable(this);
            updateAutoUi();
            return;
        }
        notificationsAsked = false;
        batteryAsked = false;
        autoSetupInProgress = true;
        continueAutoSetup();
    }

    /**
     * Konfiguracja krok po kroku: lokalizacja → „Urządzenia w pobliżu” (i powiadomienia) →
     * wybór Bluetooth auta → lokalizacja w tle (Android wymaga, żeby o nią prosić osobno).
     * Na końcu włącza automatyczny zapis.
     */
    private void continueAutoSetup() {
        if (!hasFinePermission()) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION}, REQ_AUTO_LOCATION);
            return;
        }

        java.util.List<String> needed = new java.util.ArrayList<>();
        if (!CarBluetooth.hasPermission(this)) needed.add(Manifest.permission.BLUETOOTH_CONNECT);
        if (Build.VERSION.SDK_INT >= 33 && !notificationsAsked && !Notifications.canPost(this)) {
            needed.add(Manifest.permission.POST_NOTIFICATIONS);
        }
        if (!needed.isEmpty()) {
            notificationsAsked = true;
            requestPermissions(needed.toArray(new String[0]), REQ_AUTO_FOREGROUND);
            return;
        }

        if (!CarBluetooth.isConfigured(this)) {
            chooseCarBluetooth(); // po wyborze wraca tutaj przez applyCarBluetooth()
            return;
        }

        if (!AutoParking.hasBackgroundLocationPermission(this)) {
            openDialog = new AlertDialog.Builder(this)
                    .setTitle(R.string.auto_bg_title)
                    .setMessage(R.string.auto_bg_message)
                    .setPositiveButton(R.string.auto_bg_continue, (d, w) -> requestPermissions(
                            new String[]{Manifest.permission.ACCESS_BACKGROUND_LOCATION},
                            REQ_AUTO_BACKGROUND))
                    .setNegativeButton(R.string.parking_dialog_cancel, (d, w) -> setAutoSwitch(false))
                    .setOnCancelListener(d -> setAutoSwitch(false))
                    .show();
            return;
        }

        if (!batteryAsked && !isIgnoringBatteryOptimizations()) {
            // Bez tego Android 12+ może nie pozwolić włączyć GPS w tle po połączeniu z autem.
            batteryAsked = true;
            openDialog = new AlertDialog.Builder(this)
                    .setTitle(R.string.auto_battery_title)
                    .setMessage(R.string.auto_battery_message)
                    .setPositiveButton(R.string.auto_bg_continue, (d, w) -> requestIgnoreBatteryOptimizations())
                    .setNegativeButton(R.string.auto_battery_skip, (d, w) -> continueAutoSetup())
                    .setOnCancelListener(d -> continueAutoSetup())
                    .show();
            return;
        }

        autoSetupInProgress = false;
        if (AutoParking.enable(this)) {
            Toast.makeText(this, R.string.auto_enabled_toast, Toast.LENGTH_SHORT).show();
        } else {
            setAutoSwitch(false);
        }
        updateAutoUi();
    }

    private void onAutoPermissionResult(int requestCode) {
        if (requestCode == REQ_AUTO_LOCATION && !hasFinePermission()) {
            autoSetupFailed(R.string.auto_permission_denied_location);
        } else if (requestCode == REQ_AUTO_FOREGROUND && !CarBluetooth.hasPermission(this)) {
            autoSetupFailed(R.string.bt_permission_denied);
        } else if (requestCode == REQ_AUTO_BACKGROUND && !AutoParking.hasBackgroundLocationPermission(this)) {
            autoSetupFailed(R.string.auto_permission_denied_bg);
        } else {
            refreshState();
            continueAutoSetup();
        }
    }

    private void autoSetupFailed(int messageRes) {
        setAutoSwitch(false);
        openDialog = new AlertDialog.Builder(this)
                .setTitle(R.string.auto_permission_denied_title)
                .setMessage(messageRes)
                .setPositiveButton(R.string.auto_open_settings, (d, w) -> openAppSettings())
                .setNegativeButton(R.string.parking_dialog_cancel, null)
                .show();
    }

    private void setAutoSwitch(boolean checked) {
        if (!checked) autoSetupInProgress = false;
        if (autoSwitch.isChecked() == checked) return;
        suppressSwitch = true;
        autoSwitch.setChecked(checked);
        suppressSwitch = false;
    }

    private void updateAutoUi() {
        boolean enabled = AutoParking.isEnabled(this);
        // W trakcie konfiguracji (okna uprawnień) przełącznik jest już włączony, choć ustawienie jeszcze nie.
        if (!autoSetupInProgress) setAutoSwitch(enabled);

        int color = R.color.text_secondary;
        String text;
        if (!enabled) {
            text = getString(R.string.auto_desc);
        } else if (!AutoParking.hasRequiredPermissions(this)) {
            text = getString(R.string.auto_status_missing_permissions);
            color = R.color.error;
        } else if (DrivingService.driving) {
            text = getString(R.string.auto_status_driving);
            color = R.color.ok;
        } else {
            text = getString(R.string.auto_status_on_bt);
            color = R.color.ok;
            if (!Notifications.canPost(this)) text += "\n\n" + getString(R.string.auto_status_no_notifications);
        }
        autoStatus.setText(text);
        autoStatus.setTextColor(getColor(color));

        java.util.List<String> cars = CarBluetooth.names(this);
        autoBtDevices.setText(cars.isEmpty() ? getString(R.string.bt_none)
                : getString(R.string.bt_selected, android.text.TextUtils.join(", ", cars)));

        boolean showBattery = enabled && !isIgnoringBatteryOptimizations();
        autoBatteryHint.setVisibility(showBattery ? View.VISIBLE : View.GONE);
        autoBatteryButton.setVisibility(showBattery ? View.VISIBLE : View.GONE);
    }

    /** Wybór urządzeń Bluetooth auta spośród sparowanych z telefonem. */
    private void chooseCarBluetooth() {
        if (!CarBluetooth.hasPermission(this)) {
            requestPermissions(new String[]{Manifest.permission.BLUETOOTH_CONNECT}, REQ_BT_PICK);
            return;
        }
        if (CarBluetooth.adapter(this) == null) {
            Toast.makeText(this, R.string.bt_unavailable, Toast.LENGTH_LONG).show();
            if (autoSetupInProgress) setAutoSwitch(false);
            return;
        }
        java.util.List<CarBluetooth.Device> devices = CarBluetooth.bondedDevices(this);
        if (devices.isEmpty()) {
            Toast.makeText(this, R.string.bt_no_bonded, Toast.LENGTH_LONG).show();
            if (autoSetupInProgress) setAutoSwitch(false);
            return;
        }
        java.util.Set<String> selected = CarBluetooth.addresses(this);
        String[] labels = new String[devices.size()];
        boolean[] checked = new boolean[devices.size()];
        for (int i = 0; i < devices.size(); i++) {
            CarBluetooth.Device d = devices.get(i);
            labels[i] = d.looksLikeCar ? getString(R.string.bt_car_label, d.name) : d.name;
            checked[i] = selected.contains(d.address);
        }
        openDialog = new AlertDialog.Builder(this)
                .setTitle(R.string.bt_dialog_title)
                .setMultiChoiceItems(labels, checked, (d, which, isChecked) -> checked[which] = isChecked)
                .setPositiveButton(R.string.parking_dialog_save, (d, w) -> {
                    java.util.Map<String, String> chosen = new java.util.HashMap<>();
                    for (int i = 0; i < devices.size(); i++) {
                        if (checked[i]) chosen.put(devices.get(i).address, devices.get(i).name);
                    }
                    applyCarBluetooth(chosen);
                })
                .setNeutralButton(R.string.bt_clear, (d, w) -> applyCarBluetooth(new java.util.HashMap<>()))
                .setNegativeButton(R.string.parking_dialog_cancel, (d, w) -> {
                    if (autoSetupInProgress) setAutoSwitch(false);
                })
                .setOnCancelListener(d -> {
                    if (autoSetupInProgress) setAutoSwitch(false);
                })
                .show();
    }

    private void applyCarBluetooth(java.util.Map<String, String> chosen) {
        CarBluetooth.save(this, chosen);
        EventLog.log(this, chosen.isEmpty() ? "Bluetooth auta: nie wybrano"
                : "Bluetooth auta: wybrano " + CarBluetooth.names(this));
        if (chosen.isEmpty()) {
            // Bez urządzenia auta nie ma czego nasłuchiwać.
            if (AutoParking.isEnabled(this)) AutoParking.disable(this);
            if (autoSetupInProgress) {
                Toast.makeText(this, R.string.bt_required, Toast.LENGTH_LONG).show();
            }
            setAutoSwitch(false);
        } else if (autoSetupInProgress) {
            continueAutoSetup();
        }
        updateAutoUi();
    }

    private boolean isIgnoringBatteryOptimizations() {
        PowerManager pm = getSystemService(PowerManager.class);
        return pm != null && pm.isIgnoringBatteryOptimizations(getPackageName());
    }

    @android.annotation.SuppressLint("BatteryLife") // aplikacja instalowana z pliku, nie z Google Play
    private void requestIgnoreBatteryOptimizations() {
        Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                Uri.parse("package:" + getPackageName()));
        try {
            startActivityForResult(i, REQ_BATTERY);
        } catch (ActivityNotFoundException e) {
            try {
                startActivityForResult(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS), REQ_BATTERY);
            } catch (ActivityNotFoundException e2) {
                if (autoSetupInProgress) continueAutoSetup();
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_BATTERY) return;
        EventLog.log(this, isIgnoringBatteryOptimizations()
                ? "Optymalizacja baterii wyłączona dla aplikacji" : "Optymalizacja baterii nadal włączona");
        if (autoSetupInProgress) continueAutoSetup();
        updateAutoUi();
    }


    // ------------------------------------------------------------------ akcje

    private String coordinatesText() {
        return String.format(Locale.US, "%.6f, %.6f", best.getLatitude(), best.getLongitude());
    }

    private String mapsLink() {
        return String.format(Locale.US, "https://maps.google.com/?q=%.6f,%.6f",
                best.getLatitude(), best.getLongitude());
    }

    private boolean ensurePosition() {
        if (best != null) return true;
        Toast.makeText(this, R.string.no_position_yet, Toast.LENGTH_SHORT).show();
        return false;
    }

    private void openInMaps() {
        if (!ensurePosition()) return;
        String c = String.format(Locale.US, "%.6f,%.6f", best.getLatitude(), best.getLongitude());
        Uri geo = Uri.parse("geo:" + c + "?q=" + c + "(" + Uri.encode(getString(R.string.app_name)) + ")");
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, geo));
        } catch (ActivityNotFoundException e) {
            // Brak aplikacji map: otwórz Mapy Google w przeglądarce.
            if (!startActivitySafe(new Intent(Intent.ACTION_VIEW, Uri.parse(mapsLink())))) {
                Toast.makeText(this, R.string.no_maps_app, Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void copyCoordinates() {
        if (!ensurePosition()) return;
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText(getString(R.string.app_name), coordinatesText()));
        if (Build.VERSION.SDK_INT < 33) { // od Androida 13 system sam pokazuje potwierdzenie
            Toast.makeText(this, R.string.copied, Toast.LENGTH_SHORT).show();
        }
    }

    private void shareCoordinates() {
        if (!ensurePosition()) return;
        Intent send = new Intent(Intent.ACTION_SEND)
                .setType("text/plain")
                .putExtra(Intent.EXTRA_TEXT, getString(R.string.share_text, coordinatesText(), mapsLink()));
        startActivitySafe(Intent.createChooser(send, getString(R.string.share)));
    }

    private void openAppSettings() {
        startActivitySafe(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.fromParts("package", getPackageName(), null)));
    }

    private boolean startActivitySafe(Intent intent) {
        try {
            startActivity(intent);
            return true;
        } catch (ActivityNotFoundException e) {
            return false;
        }
    }

    // ------------------------------------------------------------------ układ ekranu

    /** Od Androida 15 aplikacja rysuje pod paskami systemowymi, więc dodajemy odpowiedni margines. */
    static void applySystemBarInsets(View root) {
        final int l = root.getPaddingLeft(), t = root.getPaddingTop();
        final int r = root.getPaddingRight(), b = root.getPaddingBottom();
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                v.setPadding(l + bars.left, t + bars.top, r + bars.right, b + bars.bottom);
            } else {
                v.setPadding(l + insets.getSystemWindowInsetLeft(), t + insets.getSystemWindowInsetTop(),
                        r + insets.getSystemWindowInsetRight(), b + insets.getSystemWindowInsetBottom());
            }
            return insets;
        });
    }
}
