package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.Manifest;
import android.content.Context;
import android.content.res.Configuration;
import android.graphics.Color;

import androidx.test.core.app.ActivityScenario;
import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.rule.GrantPermissionRule;

import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Wybór motywu w aplikacji zmienia kolory ekranu niezależnie od ustawienia telefonu. */
@RunWith(AndroidJUnit4.class)
public class ThemeChooserTest {

    @Rule
    public GrantPermissionRule permissions = GrantPermissionRule.grant(
            Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION);

    private final Context context = ApplicationProvider.getApplicationContext();

    @After
    public void tearDown() {
        ThemePrefs.set(context, ThemePrefs.MODE_SYSTEM);
    }

    private static float luminance(int color) {
        return (0.2126f * Color.red(color) + 0.7152f * Color.green(color) + 0.0722f * Color.blue(color)) / 255f;
    }

    @Test
    public void darkChoiceGivesDarkScreen() {
        ThemePrefs.set(context, ThemePrefs.MODE_DARK);
        try (ActivityScenario<MainActivity> s = ActivityScenario.launch(MainActivity.class)) {
            s.onActivity(a -> {
                int night = a.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK;
                assertEquals(Configuration.UI_MODE_NIGHT_YES, night);
                assertTrue(luminance(a.getColor(R.color.background)) < 0.2f);
                assertEquals(R.id.themeDark,
                        ((android.widget.RadioGroup) a.findViewById(R.id.themeGroup)).getCheckedRadioButtonId());
            });
        }
    }

    @Test
    public void lightChoiceGivesLightScreen() {
        ThemePrefs.set(context, ThemePrefs.MODE_LIGHT);
        try (ActivityScenario<MainActivity> s = ActivityScenario.launch(MainActivity.class)) {
            s.onActivity(a -> {
                int night = a.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK;
                assertEquals(Configuration.UI_MODE_NIGHT_NO, night);
                assertTrue(luminance(a.getColor(R.color.background)) > 0.8f);
            });
        }
    }

    @Test
    public void historyScreenFollowsChoiceToo() {
        ThemePrefs.set(context, ThemePrefs.MODE_DARK);
        try (ActivityScenario<HistoryActivity> s = ActivityScenario.launch(HistoryActivity.class)) {
            s.onActivity(a -> assertTrue(luminance(a.getColor(R.color.background)) < 0.2f));
        }
    }
}
