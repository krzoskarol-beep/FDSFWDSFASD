package pl.pozycja.polska;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class AdbCommandTest {

    @Test public void grantsMockLocationOpForPackage() {
        assertEquals("adb shell appops set pl.pozycja.polska android:mock_location allow",
                MainActivity.adbCommand("pl.pozycja.polska"));
    }
}
