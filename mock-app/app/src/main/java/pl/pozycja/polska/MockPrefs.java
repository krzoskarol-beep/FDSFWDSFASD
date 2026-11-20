package pl.pozycja.polska;

import android.content.Context;
import android.content.SharedPreferences;

/** Zapamiętane miejsce docelowe (nazwa i współrzędne). */
public class MockPrefs {

    private static final String FILE = "pozycja";
    private final SharedPreferences sp;

    public MockPrefs(Context context) {
        sp = context.getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    public String name() {
        return sp.getString("name", Places.defaultPlace().name);
    }

    public double lat() {
        return Double.longBitsToDouble(sp.getLong("lat",
                Double.doubleToRawLongBits(Places.defaultPlace().lat)));
    }

    public double lon() {
        return Double.longBitsToDouble(sp.getLong("lon",
                Double.doubleToRawLongBits(Places.defaultPlace().lon)));
    }

    public void set(String name, double lat, double lon) {
        sp.edit()
                .putString("name", name)
                .putLong("lat", Double.doubleToRawLongBits(lat))
                .putLong("lon", Double.doubleToRawLongBits(lon))
                .apply();
    }

}
