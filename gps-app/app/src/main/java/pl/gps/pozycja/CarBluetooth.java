package pl.gps.pozycja;

import android.Manifest;
import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothClass;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Wybrane urządzenia Bluetooth auta (radio, zestaw głośnomówiący). Połączenie z nimi
 * oznacza początek jazdy, a rozłączenie, czyli wyłączenie silnika, jej koniec.
 * To najdokładniejsze i najszybsze źródło informacji o parkowaniu, bez fałszywych
 * alarmów w autobusie. Działa też bez usług Google Play.
 */
final class CarBluetooth {

    /** Sparowane urządzenie do wyboru w ustawieniach. */
    static final class Device {
        final String address;
        final String name;
        final boolean looksLikeCar;

        Device(String address, String name, boolean looksLikeCar) {
            this.address = address;
            this.name = name;
            this.looksLikeCar = looksLikeCar;
        }
    }

    private static final String PREFS = "car_bluetooth";
    /** Zbiór wpisów „adres|nazwa”. */
    private static final String K_DEVICES = "devices";
    /** Adresy wybranych urządzeń auta, z którymi telefon jest teraz połączony. */
    private static final String K_CONNECTED = "connected";
    private static final char SEP = '|';

    private CarBluetooth() { }

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static Set<String> entries(Context c) {
        return prefs(c).getStringSet(K_DEVICES, Collections.emptySet());
    }

    static boolean isConfigured(Context c) {
        return !entries(c).isEmpty();
    }

    static Set<String> addresses(Context c) {
        Set<String> out = new HashSet<>();
        for (String e : entries(c)) out.add(e.substring(0, Math.max(0, e.indexOf(SEP))));
        return out;
    }

    static List<String> names(Context c) {
        List<String> out = new ArrayList<>();
        for (String e : entries(c)) out.add(e.substring(e.indexOf(SEP) + 1));
        Collections.sort(out, String.CASE_INSENSITIVE_ORDER);
        return out;
    }

    static String nameFor(Context c, String address) {
        for (String e : entries(c)) {
            if (e.startsWith(address + SEP)) return e.substring(e.indexOf(SEP) + 1);
        }
        return address;
    }

    /** Zapisywane przez {@link CarBluetoothReceiver} przy każdym połączeniu i rozłączeniu. */
    static void setConnected(Context c, String address, boolean connected) {
        Set<String> set = new HashSet<>(prefs(c).getStringSet(K_CONNECTED, Collections.emptySet()));
        if (connected) set.add(address); else set.remove(address);
        prefs(c).edit().putStringSet(K_CONNECTED, set).apply();
    }

    /** Czy telefon jest teraz połączony z którymkolwiek z wybranych urządzeń auta. */
    static boolean isCarConnected(Context c) {
        Set<String> connected = prefs(c).getStringSet(K_CONNECTED, Collections.emptySet());
        for (String a : connected) {
            if (addresses(c).contains(a)) return true;
        }
        return false;
    }

    /** Po restarcie telefonu żadne połączenie nie trwa (system zgłosi je od nowa). */
    static void clearConnected(Context c) {
        prefs(c).edit().remove(K_CONNECTED).apply();
    }

    /** @param selected adres → nazwa; pusta mapa wyłącza wyzwalacz Bluetooth */
    static void save(Context c, Map<String, String> selected) {
        Set<String> set = new HashSet<>();
        for (Map.Entry<String, String> e : selected.entrySet()) set.add(e.getKey() + SEP + e.getValue());
        prefs(c).edit().putStringSet(K_DEVICES, set).apply();
    }

    /** Od Androida 12 lista sparowanych urządzeń i zdarzenia połączeń wymagają uprawnienia „Urządzenia w pobliżu”. */
    static boolean hasPermission(Context c) {
        return Build.VERSION.SDK_INT < 31
                || c.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED;
    }

    static BluetoothAdapter adapter(Context c) {
        BluetoothManager bm = c.getSystemService(BluetoothManager.class);
        return bm == null ? null : bm.getAdapter();
    }

    /** Sparowane urządzenia, najpierw te, które wyglądają na samochodowe. Pusta lista bez Bluetooth/uprawnień. */
    @SuppressLint("MissingPermission") // sprawdzane przez hasPermission()
    static List<Device> bondedDevices(Context c) {
        List<Device> out = new ArrayList<>();
        BluetoothAdapter a = adapter(c);
        if (a == null || !hasPermission(c)) return out;
        Set<BluetoothDevice> bonded;
        try {
            bonded = a.getBondedDevices();
        } catch (SecurityException e) {
            return out;
        }
        if (bonded == null) return out;
        for (BluetoothDevice d : bonded) {
            String name = d.getName();
            if (name == null || name.isEmpty()) name = d.getAddress();
            out.add(new Device(d.getAddress(), name, looksLikeCar(d)));
        }
        Collections.sort(out, (x, y) -> x.looksLikeCar != y.looksLikeCar
                ? (x.looksLikeCar ? -1 : 1)
                : x.name.compareToIgnoreCase(y.name));
        return out;
    }

    @SuppressLint("MissingPermission")
    private static boolean looksLikeCar(BluetoothDevice d) {
        try {
            BluetoothClass bc = d.getBluetoothClass();
            if (bc == null) return false;
            int dev = bc.getDeviceClass();
            return dev == BluetoothClass.Device.AUDIO_VIDEO_CAR_AUDIO
                    || dev == BluetoothClass.Device.AUDIO_VIDEO_HANDSFREE;
        } catch (SecurityException e) {
            return false;
        }
    }
}
