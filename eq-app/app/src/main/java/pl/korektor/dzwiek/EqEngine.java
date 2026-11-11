package pl.korektor.dzwiek;

import android.media.audiofx.BassBoost;
import android.media.audiofx.Equalizer;
import android.media.audiofx.Virtualizer;
import android.util.Log;

/**
 * Opakowanie na androidowe efekty audio podłączone do globalnego miksu wyjściowego
 * (sesja 0), więc korektor działa na cały dźwięk: Spotify, YouTube, odtwarzacz itd.
 *
 * Każdy efekt jest tworzony ostrożnie: na niektórych telefonach i na emulatorze
 * część z nich nie istnieje. Gdy czegoś nie ma, {@link #supported} jest false, a
 * wszystkie metody nic nie robią — aplikacja się nie wywala, tylko pokazuje komunikat.
 */
public class EqEngine {

    private static final String TAG = "EqEngine";
    /** Globalny miks wyjściowy. 0 = „output mix”, czyli cały dźwięk telefonu. */
    private static final int GLOBAL_SESSION = 0;
    /** Wyższy priorytet niż zwykłe aplikacje, by nasze ustawienia miały pierwszeństwo. */
    private static final int PRIORITY = 100;

    private Equalizer equalizer;
    private BassBoost bassBoost;
    private Virtualizer virtualizer;

    public final boolean supported;
    public final boolean bassSupported;
    public final boolean virtualizerSupported;

    private short bandCount;
    private short minLevel;
    private short maxLevel;

    public EqEngine() {
        boolean eqOk = false;
        try {
            equalizer = new Equalizer(PRIORITY, GLOBAL_SESSION);
            bandCount = equalizer.getNumberOfBands();
            short[] range = equalizer.getBandLevelRange();
            minLevel = range[0];
            maxLevel = range[1];
            eqOk = bandCount > 0;
        } catch (RuntimeException e) {
            Log.w(TAG, "Equalizer niedostępny: " + e.getMessage());
            release(equalizer);
            equalizer = null;
        }
        supported = eqOk;

        boolean bassOk = false;
        try {
            bassBoost = new BassBoost(PRIORITY, GLOBAL_SESSION);
            bassOk = bassBoost.getStrengthSupported();
        } catch (RuntimeException e) {
            Log.w(TAG, "BassBoost niedostępny: " + e.getMessage());
            release(bassBoost);
            bassBoost = null;
        }
        bassSupported = bassOk;

        boolean virtOk = false;
        try {
            virtualizer = new Virtualizer(PRIORITY, GLOBAL_SESSION);
            virtOk = virtualizer.getStrengthSupported();
        } catch (RuntimeException e) {
            Log.w(TAG, "Virtualizer niedostępny: " + e.getMessage());
            release(virtualizer);
            virtualizer = null;
        }
        virtualizerSupported = virtOk;
    }

    // ------------------------------------------------------------------ korektor
    public short bandCount() { return bandCount; }
    public short minLevel() { return minLevel; }
    public short maxLevel() { return maxLevel; }

    /** Środek pasma w Hz (API podaje mHz, zamieniamy na Hz). */
    public int centerFreqHz(short band) {
        if (equalizer == null) return 0;
        try {
            return equalizer.getCenterFreq(band) / 1000;
        } catch (RuntimeException e) {
            return 0;
        }
    }

    public short bandLevel(short band) {
        if (equalizer == null) return 0;
        try {
            return equalizer.getBandLevel(band);
        } catch (RuntimeException e) {
            return 0;
        }
    }

    public void setBandLevel(short band, short level) {
        if (equalizer == null) return;
        try {
            equalizer.setBandLevel(band, clamp(level, minLevel, maxLevel));
        } catch (RuntimeException e) {
            Log.w(TAG, "setBandLevel: " + e.getMessage());
        }
    }

    public short presetCount() {
        if (equalizer == null) return 0;
        try {
            return equalizer.getNumberOfPresets();
        } catch (RuntimeException e) {
            return 0;
        }
    }

    public String presetName(short preset) {
        if (equalizer == null) return "";
        try {
            return equalizer.getPresetName(preset);
        } catch (RuntimeException e) {
            return "";
        }
    }

    public void usePreset(short preset) {
        if (equalizer == null) return;
        try {
            equalizer.usePreset(preset);
        } catch (RuntimeException e) {
            Log.w(TAG, "usePreset: " + e.getMessage());
        }
    }

    // ------------------------------------------------------------------ bas / przestrzeń
    /** @param strength 0..1000 */
    public void setBassStrength(int strength) {
        if (bassBoost == null) return;
        try {
            bassBoost.setStrength((short) clamp(strength, 0, 1000));
        } catch (RuntimeException e) {
            Log.w(TAG, "setBass: " + e.getMessage());
        }
    }

    public short bassStrength() {
        if (bassBoost == null) return 0;
        try {
            return bassBoost.getRoundedStrength();
        } catch (RuntimeException e) {
            return 0;
        }
    }

    /** @param strength 0..1000 */
    public void setVirtualizerStrength(int strength) {
        if (virtualizer == null) return;
        try {
            virtualizer.setStrength((short) clamp(strength, 0, 1000));
        } catch (RuntimeException e) {
            Log.w(TAG, "setVirt: " + e.getMessage());
        }
    }

    public short virtualizerStrength() {
        if (virtualizer == null) return 0;
        try {
            return virtualizer.getRoundedStrength();
        } catch (RuntimeException e) {
            return 0;
        }
    }

    // ------------------------------------------------------------------ wł/wył, zwolnienie
    public void setEnabled(boolean enabled) {
        enable(equalizer, enabled);
        enable(bassBoost, enabled);
        enable(virtualizer, enabled);
    }

    public void release() {
        release(equalizer);
        release(bassBoost);
        release(virtualizer);
        equalizer = null;
        bassBoost = null;
        virtualizer = null;
    }

    private static void enable(android.media.audiofx.AudioEffect fx, boolean enabled) {
        if (fx == null) return;
        try {
            fx.setEnabled(enabled);
        } catch (RuntimeException e) {
            Log.w(TAG, "setEnabled: " + e.getMessage());
        }
    }

    private static void release(android.media.audiofx.AudioEffect fx) {
        if (fx == null) return;
        try {
            fx.release();
        } catch (RuntimeException ignored) {
        }
    }

    static short clamp(int value, int min, int max) {
        if (value < min) return (short) min;
        if (value > max) return (short) max;
        return (short) value;
    }
}
