package pl.korektor.dzwiek;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * Zapamiętane ustawienia korektora: czy włączony, wybrany zestaw (preset),
 * poziomy pasm, siła basu i efektu przestrzennego. Przechowywane w SharedPreferences.
 */
public class EqPrefs {

    private static final String FILE = "korektor";
    private static final String ENABLED = "enabled";
    private static final String PRESET = "preset";          // -1 = własne ustawienia
    private static final String BANDS = "bands";            // poziomy pasm po przecinku
    private static final String BASS = "bass";
    private static final String VIRT = "virt";

    public static final short PRESET_CUSTOM = -1;

    private final SharedPreferences sp;

    public EqPrefs(Context context) {
        sp = context.getApplicationContext().getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    public boolean isEnabled() { return sp.getBoolean(ENABLED, false); }
    public void setEnabled(boolean v) { sp.edit().putBoolean(ENABLED, v).apply(); }

    public short preset() { return (short) sp.getInt(PRESET, PRESET_CUSTOM); }
    public void setPreset(short v) { sp.edit().putInt(PRESET, v).apply(); }

    public int bass() { return sp.getInt(BASS, 0); }
    public void setBass(int v) { sp.edit().putInt(BASS, v).apply(); }

    public int virtualizer() { return sp.getInt(VIRT, 0); }
    public void setVirtualizer(int v) { sp.edit().putInt(VIRT, v).apply(); }

    /** Poziomy pasm (miliB) albo null, gdy jeszcze nic nie zapisano. */
    public short[] bandLevels() {
        String raw = sp.getString(BANDS, null);
        return decode(raw);
    }

    public void setBandLevels(short[] levels) {
        sp.edit().putString(BANDS, encode(levels)).apply();
    }

    // ------------------------------------------------------------------ kodowanie listy
    static String encode(short[] levels) {
        if (levels == null || levels.length == 0) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < levels.length; i++) {
            if (i > 0) sb.append(',');
            sb.append((int) levels[i]);
        }
        return sb.toString();
    }

    static short[] decode(String raw) {
        if (raw == null || raw.isEmpty()) return null;
        String[] parts = raw.split(",");
        short[] out = new short[parts.length];
        for (int i = 0; i < parts.length; i++) {
            try {
                out[i] = (short) Integer.parseInt(parts[i].trim());
            } catch (NumberFormatException e) {
                out[i] = 0;
            }
        }
        return out;
    }
}
