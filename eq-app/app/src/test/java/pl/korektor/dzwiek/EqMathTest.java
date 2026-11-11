package pl.korektor.dzwiek;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class EqMathTest {

    private static final short MIN = -1500, MAX = 1500;

    @Test public void centreIsHalf() {
        assertEquals(0.5f, EqMath.levelToFraction((short) 0, MIN, MAX), 0.0001f);
    }

    @Test public void topAndBottom() {
        assertEquals(1.0f, EqMath.levelToFraction(MAX, MIN, MAX), 0.0001f);
        assertEquals(0.0f, EqMath.levelToFraction(MIN, MIN, MAX), 0.0001f);
    }

    @Test public void fractionRoundTrips() {
        assertEquals(0, EqMath.fractionToLevel(0.5f, MIN, MAX));
        assertEquals(MAX, EqMath.fractionToLevel(1.0f, MIN, MAX));
        assertEquals(MIN, EqMath.fractionToLevel(0.0f, MIN, MAX));
    }

    @Test public void fractionClamps() {
        assertEquals(MAX, EqMath.fractionToLevel(2.0f, MIN, MAX));
        assertEquals(MIN, EqMath.fractionToLevel(-1.0f, MIN, MAX));
    }

    @Test public void formatDbSigns() {
        assertEquals("0 dB", EqMath.formatDb((short) 0));
        assertEquals("+3.0 dB", EqMath.formatDb((short) 300));
        assertEquals("−6.0 dB", EqMath.formatDb((short) -600));
    }

    @Test public void formatFreqUnits() {
        assertEquals("60 Hz", EqMath.formatFreq(60));
        assertEquals("230 Hz", EqMath.formatFreq(230));
        assertEquals("1.0 kHz", EqMath.formatFreq(1000));
        assertEquals("3.6 kHz", EqMath.formatFreq(3600));
        assertEquals("14 kHz", EqMath.formatFreq(14000));
    }
}
