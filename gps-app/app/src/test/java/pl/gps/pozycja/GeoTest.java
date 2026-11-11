package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class GeoTest {

    // Pałac Kultury i Nauki oraz Zamek Królewski w Warszawie
    private static final double PKIN_LAT = 52.231838, PKIN_LON = 21.005995;
    private static final double ZAMEK_LAT = 52.247950, ZAMEK_LON = 21.015320;

    @Test
    public void distance_warsawLandmarks() {
        // ok. 1,92 km w linii prostej
        assertEquals(1920, Geo.distanceMeters(PKIN_LAT, PKIN_LON, ZAMEK_LAT, ZAMEK_LON), 20);
    }

    @Test
    public void distance_samePointIsZero() {
        assertEquals(0, Geo.distanceMeters(PKIN_LAT, PKIN_LON, PKIN_LAT, PKIN_LON), 1e-6);
    }

    @Test
    public void distance_oneDegreeOfLatitude() {
        assertEquals(111_195, Geo.distanceMeters(50, 20, 51, 20), 50);
    }

    @Test
    public void bearing_cardinalDirections() {
        assertEquals(0, Geo.bearingDegrees(50, 20, 50.01, 20), 0.01);    // na północ
        assertEquals(180, Geo.bearingDegrees(50, 20, 49.99, 20), 0.01);  // na południe
        assertEquals(90, Geo.bearingDegrees(50, 20, 50, 20.01), 0.01);   // na wschód
        assertEquals(270, Geo.bearingDegrees(50, 20, 50, 19.99), 0.01);  // na zachód
    }

    @Test
    public void bearing_castleIsNorthNorthEastOfPalace() {
        double b = Geo.bearingDegrees(PKIN_LAT, PKIN_LON, ZAMEK_LAT, ZAMEK_LON);
        assertEquals(20, b, 3);
        assertEquals("Pn", Formatters.compassDirection((float) b));
    }

    @Test
    public void normalizeDegrees_wrapsIntoRange() {
        assertEquals(350, Geo.normalizeDegrees(-10), 1e-9);
        assertEquals(10, Geo.normalizeDegrees(370), 1e-9);
        assertEquals(0, Geo.normalizeDegrees(360), 1e-9);
    }

    @Test
    public void formatDistance_units() {
        assertEquals("8 m", Formatters.formatDistance(7.6));
        assertEquals("350 m", Formatters.formatDistance(350.2));
        assertEquals("1,2 km", Formatters.formatDistance(1234));
        assertEquals("15 km", Formatters.formatDistance(15_400));
    }
}
