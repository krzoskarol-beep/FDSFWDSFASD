package pl.pozycja.polska;

import android.annotation.SuppressLint;
import android.app.AppOpsManager;
import android.content.Context;
import android.location.Criteria;
import android.location.Location;
import android.location.LocationManager;
import android.location.provider.ProviderProperties;
import android.os.Build;
import android.os.Process;
import android.os.SystemClock;

import java.util.ArrayList;
import java.util.List;

/**
 * Podstawia pozycję przez oficjalny mechanizm Androida „aplikacja do pozorowania
 * lokalizacji” (Opcje programisty). Rejestruje dostawców testowych w miejsce GPS,
 * sieci i (od Androida 12) dostawcy „fused”, a potem wysyła do nich wybraną pozycję.
 * Działa tylko wtedy, gdy użytkownik wybrał tę aplikację w Opcjach programisty.
 */
public class MockEngine {

    private final Context context;
    private final LocationManager lm;
    private final List<String> active = new ArrayList<>();

    public MockEngine(Context context) {
        this.context = context.getApplicationContext();
        this.lm = this.context.getSystemService(LocationManager.class);
    }

    /** Czy aplikacja jest wybrana jako „aplikacja do pozorowania lokalizacji”. */
    public static boolean isAllowed(Context context) {
        AppOpsManager ops = context.getSystemService(AppOpsManager.class);
        if (ops == null) return false;
        try {
            int mode = ops.checkOpNoThrow(AppOpsManager.OPSTR_MOCK_LOCATION,
                    Process.myUid(), context.getPackageName());
            return mode == AppOpsManager.MODE_ALLOWED;
        } catch (RuntimeException e) {
            return false;
        }
    }

    /** Dostawcy, których podmieniamy. */
    static String[] providers() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            return new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER,
                    LocationManager.FUSED_PROVIDER};
        }
        return new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER};
    }

    /**
     * Rejestruje dostawców testowych.
     *
     * @throws SecurityException gdy aplikacja nie jest wybrana w Opcjach programisty
     */
    public void start() {
        if (!active.isEmpty()) return;
        SecurityException denied = null;
        for (String p : providers()) {
            try {
                addProvider(p);
                lm.setTestProviderEnabled(p, true);
                active.add(p);
            } catch (SecurityException e) {
                denied = e;
            } catch (RuntimeException e) {
                // Pojedynczy dostawca może nie istnieć na danym telefonie. Pomijamy go.
            }
        }
        if (active.isEmpty() && denied != null) throw denied;
        if (active.isEmpty()) throw new IllegalStateException("Brak dostawcy lokalizacji do podmiany");
    }

    private void addProvider(String p) {
        try {
            addProviderOnce(p);
        } catch (IllegalArgumentException e) {
            // Został po poprzednim, przerwanym uruchomieniu: usuń i dodaj od nowa.
            try { lm.removeTestProvider(p); } catch (RuntimeException ignored) { }
            addProviderOnce(p);
        }
    }

    // Stałe Criteria.POWER_LOW i ACCURACY_FINE mają te same wartości (1), których oczekuje
    // starsze addTestProvider; lint myli je z adnotacją nowszych ProviderProperties.
    @SuppressLint("WrongConstant")
    @SuppressWarnings("deprecation")
    private void addProviderOnce(String p) {
        boolean network = LocationManager.NETWORK_PROVIDER.equals(p);
        boolean gps = LocationManager.GPS_PROVIDER.equals(p);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            ProviderProperties props = new ProviderProperties.Builder()
                    .setHasNetworkRequirement(network)
                    .setHasSatelliteRequirement(gps)
                    .setHasAltitudeSupport(true)
                    .setHasSpeedSupport(true)
                    .setHasBearingSupport(true)
                    .setPowerUsage(ProviderProperties.POWER_USAGE_LOW)
                    .setAccuracy(ProviderProperties.ACCURACY_FINE)
                    .build();
            lm.addTestProvider(p, props);
        } else {
            lm.addTestProvider(p, network, gps, false, false, true, true, true,
                    Criteria.POWER_LOW, Criteria.ACCURACY_FINE);
        }
    }

    /** Czy dostawcy testowi są zarejestrowani. */
    public boolean isStarted() {
        return !active.isEmpty();
    }

    /** Wysyła pozycję do wszystkich podmienionych dostawców. */
    public void push(double lat, double lon, float accuracyMeters) {
        for (String p : active) {
            try {
                lm.setTestProviderLocation(p, build(p, lat, lon, accuracyMeters));
            } catch (RuntimeException ignored) {
                // np. użytkownik w międzyczasie odebrał zgodę; usługa sprawdzi to sama
            }
        }
    }

    static Location build(String provider, double lat, double lon, float accuracy) {
        Location l = new Location(provider);
        l.setLatitude(lat);
        l.setLongitude(lon);
        l.setAltitude(110.0);
        l.setAccuracy(accuracy);
        l.setSpeed(0f);
        l.setBearing(0f);
        l.setTime(System.currentTimeMillis());
        l.setElapsedRealtimeNanos(SystemClock.elapsedRealtimeNanos());
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            l.setVerticalAccuracyMeters(accuracy * 1.5f);
            l.setSpeedAccuracyMetersPerSecond(0.1f);
            l.setBearingAccuracyDegrees(10f);
        }
        return l;
    }

    /** Usuwa dostawców testowych: telefon wraca do prawdziwej pozycji. */
    public void stop() {
        for (String p : active) {
            try {
                lm.removeTestProvider(p);
            } catch (RuntimeException ignored) { }
        }
        active.clear();
    }
}
