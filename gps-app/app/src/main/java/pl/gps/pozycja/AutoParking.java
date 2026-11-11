package pl.gps.pozycja;

import android.Manifest;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

/**
 * Automatyczne zapisywanie parkowania na podstawie Bluetooth auta:
 * połączenie z autem = początek jazdy, rozłączenie (wyłączenie silnika) = zapis parkingu.
 * Zdarzenia odbiera {@link CarBluetoothReceiver} zarejestrowany w manifeście, więc
 * nic nie trzeba rejestrować w systemie. Nie korzysta z usług Google Play.
 */
final class AutoParking {

    private static final String PREFS = "auto_parking";
    private static final String K_ENABLED = "enabled";

    private AutoParking() { }

    /** Włączone przez użytkownika i z wybranym Bluetooth auta. */
    static boolean isEnabled(Context c) {
        return prefs(c).getBoolean(K_ENABLED, false);
    }

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static boolean hasBackgroundLocationPermission(Context c) {
        return Build.VERSION.SDK_INT < 29
                || c.checkSelfPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }

    /** Wszystko, bez czego zapis w tle nie zadziała (powiadomienia są opcjonalne). */
    static boolean hasRequiredPermissions(Context c) {
        return c.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                && hasBackgroundLocationPermission(c)
                && CarBluetooth.hasPermission(c);
    }

    /** Włącza automatyczny zapis. Wymaga wybranego Bluetooth auta i przyznanych uprawnień. */
    static boolean enable(Context context) {
        Context c = context.getApplicationContext();
        if (!CarBluetooth.isConfigured(c)) {
            EventLog.log(c, "Nie można włączyć: nie wybrano Bluetooth auta");
            return false;
        }
        if (!hasRequiredPermissions(c)) {
            EventLog.log(c, "Nie można włączyć: brak uprawnień");
            return false;
        }
        prefs(c).edit().putBoolean(K_ENABLED, true).apply();
        EventLog.log(c, "Automatyczne zapisywanie włączone, Bluetooth auta: " + CarBluetooth.names(c));
        return true;
    }

    static void disable(Context context) {
        Context c = context.getApplicationContext();
        prefs(c).edit().putBoolean(K_ENABLED, false).apply();
        EventLog.log(c, "Automatyczne zapisywanie wyłączone");
        DrivingService.cancel(c);
    }

    /** Po restarcie telefonu / aktualizacji: tylko sprawdzenie, czy nadal mamy uprawnienia. */
    static void checkAfterBoot(Context c) {
        if (isEnabled(c) && !hasRequiredPermissions(c)) {
            EventLog.log(c, "UWAGA: automatyczne zapisywanie włączone, ale brakuje uprawnień");
        }
    }
}
