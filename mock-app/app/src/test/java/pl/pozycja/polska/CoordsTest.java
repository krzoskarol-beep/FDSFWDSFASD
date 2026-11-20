package pl.pozycja.polska;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Random;

public class CoordsTest {

    private static final double EPS = 1e-9;

    @Test public void parsesGoogleMapsCopy() {
        assertArrayEquals(new double[]{52.2297, 21.0122}, Coords.parse("52.2297, 21.0122"), EPS);
    }

    @Test public void parsesWithoutSpaceAndWithSpaceOnly() {
        assertArrayEquals(new double[]{50.06, 19.93}, Coords.parse("50.06,19.93"), EPS);
        assertArrayEquals(new double[]{50.06, 19.93}, Coords.parse("  50.06 19.93 "), EPS);
        assertArrayEquals(new double[]{50.06, 19.93}, Coords.parse("50.06;19.93"), EPS);
    }

    @Test public void parsesDecimalComma() {
        assertArrayEquals(new double[]{52.2297, 21.0122}, Coords.parse("52,2297, 21,0122"), EPS);
        assertArrayEquals(new double[]{52.2297, 21.0122}, Coords.parse("52,2297 21,0122"), EPS);
        assertArrayEquals(new double[]{52.2297, 21.0122}, Coords.parse("52,2297;21,0122"), EPS);
    }

    @Test public void parsesGoogleMapsLink() {
        double[] c = Coords.parse("https://www.google.com/maps/@54.352,18.6466,15z");
        assertArrayEquals(new double[]{54.352, 18.6466}, c, EPS);
    }

    @Test public void parsesIntegersAndNegative() {
        assertArrayEquals(new double[]{52, 21}, Coords.parse("52, 21"), EPS);
        assertArrayEquals(new double[]{-33.86, 151.2}, Coords.parse("-33.86, 151.2"), EPS);
    }

    @Test public void rejectsGarbageAndOutOfRange() {
        assertNull(Coords.parse(null));
        assertNull(Coords.parse(""));
        assertNull(Coords.parse("Warszawa"));
        assertNull(Coords.parse("52.2"));
        assertNull(Coords.parse("95.0, 21.0"));
        assertNull(Coords.parse("52.0, 190.0"));
    }

    @Test public void polandBounds() {
        for (Places.Place p : Places.ALL) {
            assertTrue(p.name, Coords.inPoland(p.lat, p.lon));
        }
        assertFalse(Coords.inPoland(52.52, 13.405));   // Berlin
        assertFalse(Coords.inPoland(51.5072, -0.1276)); // Londyn
        assertFalse(Coords.inPoland(48.2082, 16.3738)); // Wiedeń
    }

    @Test public void jitterStaysWithinRadius() {
        Random rnd = new Random(42);
        double lat = 52.2297, lon = 21.0122;
        double maxSeen = 0;
        for (int i = 0; i < 5000; i++) {
            double[] j = Coords.jitter(lat, lon, 4.0, rnd);
            double d = Coords.distanceMeters(lat, lon, j[0], j[1]);
            assertTrue("odległość " + d, d <= 4.0 + 1e-3);
            maxSeen = Math.max(maxSeen, d);
        }
        assertTrue("drgania powinny być widoczne", maxSeen > 3.0);
    }

    @Test public void distanceWarsawKrakow() {
        Places.Place w = Places.byName("Warszawa");
        Places.Place k = Places.byName("Kraków");
        double km = Coords.distanceMeters(w.lat, w.lon, k.lat, k.lon) / 1000;
        assertEquals(252, km, 5);
    }

    @Test public void formatUsesDot() {
        assertEquals("52.22970, 21.01220", Coords.format(52.2297, 21.0122));
    }

    @Test public void placesLookup() {
        assertEquals("Warszawa", Places.defaultPlace().name);
        assertEquals(50.0614, Places.byName("Kraków").lat, EPS);
        assertNull(Places.byName("Berlin"));
        assertNull(Places.byName(null));
    }
}
