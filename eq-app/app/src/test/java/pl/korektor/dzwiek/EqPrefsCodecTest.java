package pl.korektor.dzwiek;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import org.junit.Test;

public class EqPrefsCodecTest {

    @Test public void encodeThenDecodeRoundTrips() {
        short[] in = {0, 300, -600, 1500};
        String raw = EqPrefs.encode(in);
        assertEquals("0,300,-600,1500", raw);
        assertArrayEquals(in, EqPrefs.decode(raw));
    }

    @Test public void emptyAndNull() {
        assertEquals("", EqPrefs.encode(null));
        assertEquals("", EqPrefs.encode(new short[0]));
        assertNull(EqPrefs.decode(null));
        assertNull(EqPrefs.decode(""));
    }

    @Test public void badNumbersBecomeZero() {
        assertArrayEquals(new short[]{0, 5, 0}, EqPrefs.decode("x,5, "));
    }
}
