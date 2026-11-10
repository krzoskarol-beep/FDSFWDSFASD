package pl.gps.pozycja;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Insets;
import android.location.GnssStatus;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
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

    // ------------------------------------------------------------------ cykl życia

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

        applySystemBarInsets(findViewById(R.id.root));

        if (!hasAnyLocationPermission()) {
            requestLocationPermission();
        }
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
        handler.post(ticker);
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(providersChanged);
        handler.removeCallbacks(ticker);
        stopUpdates();
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
    private static void applySystemBarInsets(View root) {
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
