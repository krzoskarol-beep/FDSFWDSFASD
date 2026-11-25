package pl.godziny.praca;

import static org.junit.Assert.assertEquals;

import android.content.res.Configuration;

import org.junit.Test;

public class ThemePrefsTest {

    private static final int PHONE_DAY = Configuration.UI_MODE_TYPE_NORMAL | Configuration.UI_MODE_NIGHT_NO;
    private static final int PHONE_NIGHT = Configuration.UI_MODE_TYPE_NORMAL | Configuration.UI_MODE_NIGHT_YES;

    @Test public void systemKeepsPhoneSetting() {
        assertEquals(PHONE_DAY, ThemePrefs.uiModeFor(ThemePrefs.MODE_SYSTEM, PHONE_DAY));
        assertEquals(PHONE_NIGHT, ThemePrefs.uiModeFor(ThemePrefs.MODE_SYSTEM, PHONE_NIGHT));
    }

    @Test public void forcedModesOverrideOnlyNightBits() {
        assertEquals(PHONE_NIGHT, ThemePrefs.uiModeFor(ThemePrefs.MODE_DARK, PHONE_DAY));
        assertEquals(PHONE_DAY, ThemePrefs.uiModeFor(ThemePrefs.MODE_LIGHT, PHONE_NIGHT));
        assertEquals(Configuration.UI_MODE_TYPE_NORMAL | Configuration.UI_MODE_NIGHT_YES,
                ThemePrefs.uiModeFor(ThemePrefs.MODE_DARK, Configuration.UI_MODE_TYPE_NORMAL));
    }
}
