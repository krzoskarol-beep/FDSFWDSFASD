package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class FormattersTest {

    @Test
    public void toDms_warsawLatitude() {
        // Pałac Kultury: 52.231667 N
        assertEquals("52° 13' 54.0\" N", Formatters.toDms(52.231667, true));
    }

    @Test
    public void toDms_negativeValuesUseSouthAndWest() {
        assertEquals("33° 51' 54.5\" S", Formatters.toDms(-33.865143, true));
        assertEquals("0° 07' 39.1\" W", Formatters.toDms(-0.127528, false));
    }

    @Test
    public void toDms_roundsUpInsteadOfShowingSixtySeconds() {
        // 10.9999999° nie może dać 10° 59' 60.0"
        assertEquals("11° 00' 00.0\" E", Formatters.toDms(10.9999999, false));
    }

    @Test
    public void compassDirection_coversAllSectors() {
        assertEquals("Pn", Formatters.compassDirection(0f));
        assertEquals("Pn", Formatters.compassDirection(359f));
        assertEquals("Pn-Wsch", Formatters.compassDirection(45f));
        assertEquals("Wsch", Formatters.compassDirection(90f));
        assertEquals("Pd", Formatters.compassDirection(180f));
        assertEquals("Zach", Formatters.compassDirection(270f));
        assertEquals("Pn-Zach", Formatters.compassDirection(315f));
    }

    @Test
    public void formatAge_picksSensibleUnit() {
        assertEquals("0 s", Formatters.formatAge(-500));
        assertEquals("42 s", Formatters.formatAge(42_000));
        assertEquals("5 min", Formatters.formatAge(5 * 60_000));
        assertEquals("3 h", Formatters.formatAge(3 * 3_600_000L));
        assertEquals("2 dni", Formatters.formatAge(50 * 3_600_000L));
    }
}
