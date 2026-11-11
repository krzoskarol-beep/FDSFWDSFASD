package pl.korektor.dzwiek;

import java.util.Locale;

/**
 * Czyste przeliczenia bez zależności od Androida (łatwe do testów):
 * poziom pasma w miliB ↔ ułamek suwaka, oraz formatowanie dB i Hz dla etykiet.
 */
public final class EqMath {

    private EqMath() {}

    /** Poziom (miliB) na ułamek 0..1 dla suwaka, gdzie min=dół, max=góra. */
    public static float levelToFraction(short level, short min, short max) {
        if (max == min) return 0.5f;
        float f = (float) (level - min) / (float) (max - min);
        return clamp01(f);
    }

    /** Ułamek 0..1 na poziom pasma (miliB). */
    public static short fractionToLevel(float fraction, short min, short max) {
        float f = clamp01(fraction);
        return (short) Math.round(min + f * (max - min));
    }

    private static float clamp01(float f) {
        if (f < 0f) return 0f;
        if (f > 1f) return 1f;
        return f;
    }

    /** Poziom pasma na opis dB, np. „+3.0 dB”, „0 dB”, „−6.0 dB”. */
    public static String formatDb(short millibel) {
        float db = millibel / 100f;
        if (Math.abs(db) < 0.05f) return "0 dB";
        String sign = db > 0 ? "+" : "−"; // prawdziwy minus
        return sign + String.format(Locale.US, "%.1f dB", Math.abs(db));
    }

    /** Częstotliwość w Hz na krótki opis, np. „60 Hz”, „1.0 kHz”, „14 kHz”. */
    public static String formatFreq(int hz) {
        if (hz < 1000) return hz + " Hz";
        float khz = hz / 1000f;
        if (khz < 10f) return String.format(Locale.US, "%.1f kHz", khz);
        return Math.round(khz) + " kHz";
    }
}
