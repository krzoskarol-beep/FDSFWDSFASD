package pl.gps.pozycja;

/** Obliczenia na kuli ziemskiej, bez zależności od Androida (łatwe do testowania). */
final class Geo {

    /** Średni promień Ziemi w metrach (IUGG). */
    private static final double EARTH_RADIUS_M = 6_371_008.8;

    private Geo() { }

    /** Odległość po powierzchni Ziemi (wzór haversine), w metrach. */
    static double distanceMeters(double lat1, double lon1, double lat2, double lon2) {
        double p1 = Math.toRadians(lat1), p2 = Math.toRadians(lat2);
        double dp = p2 - p1;
        double dl = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dp / 2) * Math.sin(dp / 2)
                + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
        return 2 * EARTH_RADIUS_M * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    /** Kierunek z punktu 1 do punktu 2 względem północy geograficznej, 0–360°. */
    static double bearingDegrees(double lat1, double lon1, double lat2, double lon2) {
        double p1 = Math.toRadians(lat1), p2 = Math.toRadians(lat2);
        double dl = Math.toRadians(lon2 - lon1);
        double y = Math.sin(dl) * Math.cos(p2);
        double x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
        return normalizeDegrees(Math.toDegrees(Math.atan2(y, x)));
    }

    static double normalizeDegrees(double deg) {
        double d = deg % 360;
        return d < 0 ? d + 360 : d;
    }
}
