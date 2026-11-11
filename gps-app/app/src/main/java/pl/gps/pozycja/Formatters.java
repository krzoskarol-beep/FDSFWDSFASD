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

    private static final Locale POLISH = Locale.forLanguageTag("pl-PL");

    /** „8 m”, „350 m”, „1,2 km”, „15 km”. */
    static String formatDistance(double meters) {
        if (meters < 1000) return Math.round(meters) + " m";
        if (meters < 10_000) return String.format(POLISH, "%.1f km", meters / 1000);
        return Math.round(meters / 1000) + " km";
    }

    /**
     * Krótki adres do wyświetlenia: „Marszałkowska 10, Warszawa”. Gdy brak ulicy,
     * używa pełnej linii adresu z Geocodera. Zwraca pusty tekst, jeśli nic nie wiadomo.
     */
    static String formatAddress(String street, String number, String city, String fullLine) {
        StringBuilder sb = new StringBuilder();
        if (notEmpty(street)) {
            sb.append(street.trim());
            if (notEmpty(number)) sb.append(' ').append(number.trim());
        }
        if (notEmpty(city) && !(sb.length() > 0 && sb.toString().contains(city.trim()))) {
            if (sb.length() > 0) sb.append(", ");
            sb.append(city.trim());
        }
        if (sb.length() == 0 || !notEmpty(street)) {
            if (notEmpty(fullLine)) return fullLine.trim();
        }
        return sb.toString();
    }

    private static boolean notEmpty(String s) {
        return s != null && !s.trim().isEmpty();
    }

    /**
     * Kierunek do auta względem tego, gdzie patrzysz (kąt strzałki, 0° = przed Tobą,
     * zgodnie z ruchem wskazówek zegara): „prosto”, „lekko w prawo”, „za Tobą”…
     */
    static String relativeDirection(float arrowDegrees) {
        double a = Geo.normalizeDegrees(arrowDegrees);
        if (a < 20 || a >= 340) return "prosto";
        if (a < 60) return "lekko w prawo";
        if (a < 135) return "w prawo";
        if (a < 225) return "za Tobą";
        if (a < 300) return "w lewo";
        return "lekko w lewo";
    }
}
