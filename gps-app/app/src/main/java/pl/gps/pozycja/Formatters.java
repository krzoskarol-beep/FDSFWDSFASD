package pl.gps.pozycja;

import java.util.Locale;

/** Czyste funkcje formatujące, bez zależności od Androida (łatwe do testowania). */
final class Formatters {

    private Formatters() { }

    static String formatAge(long ms) {
        long s = Math.max(0, ms / 1000);
        if (s < 60) return s + " s";
        long m = s / 60;
        if (m < 60) return m + " min";
        long h = m / 60;
        if (h < 48) return h + " h";
        return (h / 24) + " dni";
    }

    static String toDms(double value, boolean isLatitude) {
        String hemi = isLatitude ? (value >= 0 ? "N" : "S") : (value >= 0 ? "E" : "W");
        double abs = Math.abs(value);
        int deg = (int) abs;
        double minFull = (abs - deg) * 60;
        int min = (int) minFull;
        double sec = (minFull - min) * 60;
        if (sec >= 59.95) { sec = 0; min++; }
        if (min >= 60) { min = 0; deg++; }
        return String.format(Locale.US, "%d° %02d' %04.1f\" %s", deg, min, sec, hemi);
    }

    static String compassDirection(float degrees) {
        String[] dirs = {"Pn", "Pn-Wsch", "Wsch", "Pd-Wsch", "Pd", "Pd-Zach", "Zach", "Pn-Zach"};
        return dirs[(int) Math.floor(((degrees % 360) + 360 + 22.5) % 360 / 45)];
    }
}
