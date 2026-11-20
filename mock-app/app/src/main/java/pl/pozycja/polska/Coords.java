package pl.pozycja.polska;

import java.util.Locale;
import java.util.Random;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Współrzędne: odczyt z tekstu, sprawdzenie, czy leżą w Polsce, i drobne drgania. */
public final class Coords {

    private Coords() {}

    /** Prostokąt obejmujący całą Polskę (z niewielkim zapasem). */
    public static final double PL_MIN_LAT = 49.0, PL_MAX_LAT = 54.9;
    public static final double PL_MIN_LON = 14.1, PL_MAX_LON = 24.2;

    private static final double EARTH_RADIUS_M = 6_371_000.0;

    /** Dwie liczby dziesiętne oddzielone przecinkiem, średnikiem lub spacją. */
    private static final Pattern PAIR = Pattern.compile(
            "(-?\\d{1,3}(?:[.,]\\d+)?)\\s*[,; ]\\s*(-?\\d{1,3}(?:[.,]\\d+)?)");

    /**
     * Czyta parę „szerokość, długość”, np. „52.2297, 21.0122” skopiowane z Map Google,
     * także z przecinkiem dziesiętnym („52,2297 21,0122”) albo z linku zawierającego
     * „@52.2297,21.0122”. Zwraca {lat, lon} albo {@code null}, gdy tekstu nie da się
     * odczytać lub wartości są poza zakresem.
     */
    public static double[] parse(String text) {
        if (text == null) return null;
        String t = text.trim();
        if (t.isEmpty()) return null;

        int at = t.indexOf('@');
        if (at >= 0) t = t.substring(at + 1);

        // „52,2297, 21,0122”: przecinek dziesiętny i przecinek rozdzielający naraz.
        Matcher m = Pattern.compile("^(-?\\d{1,3}),(\\d+)\\s*[,; ]\\s*(-?\\d{1,3}),(\\d+)").matcher(t);
        double lat, lon;
        if (m.find()) {
            lat = Double.parseDouble(m.group(1) + "." + m.group(2));
            lon = Double.parseDouble(m.group(3) + "." + m.group(4));
        } else {
            m = PAIR.matcher(t);
            if (!m.find()) return null;
            lat = Double.parseDouble(m.group(1).replace(',', '.'));
            lon = Double.parseDouble(m.group(2).replace(',', '.'));
        }
        if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
        return new double[]{lat, lon};
    }

    /** Czy punkt leży w prostokącie Polski. */
    public static boolean inPoland(double lat, double lon) {
        return lat >= PL_MIN_LAT && lat <= PL_MAX_LAT && lon >= PL_MIN_LON && lon <= PL_MAX_LON;
    }

    /**
     * Przesuwa punkt losowo o co najwyżej {@code maxMeters} metrów. Pozycja, która
     * nigdy się nie zmienia nawet o centymetr, wygląda nienaturalnie; prawdziwy GPS
     * stale lekko „pływa”.
     */
    public static double[] jitter(double lat, double lon, double maxMeters, Random rnd) {
        double dist = maxMeters * Math.sqrt(rnd.nextDouble()); // równomiernie w kole
        double angle = rnd.nextDouble() * 2 * Math.PI;
        double dLat = (dist * Math.cos(angle)) / EARTH_RADIUS_M;
        double dLon = (dist * Math.sin(angle)) / (EARTH_RADIUS_M * Math.cos(Math.toRadians(lat)));
        return new double[]{lat + Math.toDegrees(dLat), lon + Math.toDegrees(dLon)};
    }

    /** Odległość w metrach (wzór haversine). */
    public static double distanceMeters(double lat1, double lon1, double lat2, double lon2) {
        double p1 = Math.toRadians(lat1), p2 = Math.toRadians(lat2);
        double dp = p2 - p1, dl = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dp / 2) * Math.sin(dp / 2)
                + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
        return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(a)));
    }

    /** „52.22970, 21.01220” – zawsze kropka, niezależnie od języka telefonu. */
    public static String format(double lat, double lon) {
        return String.format(Locale.US, "%.5f, %.5f", lat, lon);
    }
}
