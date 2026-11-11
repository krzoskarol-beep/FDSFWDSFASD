package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;

import android.content.res.Configuration;

import org.junit.Test;

public class ThemePrefsTest {

    private static final int OTHER_BITS = Configuration.UI_MODE_TYPE_NORMAL;
    private static final int SYSTEM_DARK = OTHER_BITS | Configuration.UI_MODE_NIGHT_YES;
    private static final int SYSTEM_LIGHT = OTHER_BITS | Configuration.UI_MODE_NIGHT_NO;

    @Test
    public void systemModeKeepsWhatThePhoneUses() {
        assertEquals(SYSTEM_DARK, ThemePrefs.uiModeFor(ThemePrefs.MODE_SYSTEM, SYSTEM_DARK));
        assertEquals(SYSTEM_LIGHT, ThemePrefs.uiModeFor(ThemePrefs.MODE_SYSTEM, SYSTEM_LIGHT));
    }

    @Test
    public void darkModeForcesNightEvenWhenPhoneIsLight() {
        assertEquals(SYSTEM_DARK, ThemePrefs.uiModeFor(ThemePrefs.MODE_DARK, SYSTEM_LIGHT));
    }

    @Test
    public void lightModeForcesDayEvenWhenPhoneIsDark() {
        assertEquals(SYSTEM_LIGHT, ThemePrefs.uiModeFor(ThemePrefs.MODE_LIGHT, SYSTEM_DARK));
    }

    @Test
    public void otherUiModeBitsArePreserved() {
        int car = Configuration.UI_MODE_TYPE_CAR | Configuration.UI_MODE_NIGHT_NO;
        assertEquals(Configuration.UI_MODE_TYPE_CAR | Configuration.UI_MODE_NIGHT_YES,
                ThemePrefs.uiModeFor(ThemePrefs.MODE_DARK, car));
    }

    @Test
    public void unknownStoredValueBehavesLikeSystem() {
        assertEquals(SYSTEM_DARK, ThemePrefs.uiModeFor(42, SYSTEM_DARK));
    }
}
