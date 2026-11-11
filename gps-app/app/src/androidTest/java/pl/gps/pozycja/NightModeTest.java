package pl.gps.pozycja;

import static org.junit.Assert.assertTrue;

import android.content.Context;
import android.content.res.Configuration;
import android.graphics.Color;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class NightModeTest {

    private static Context withNight(boolean night) {
        Context base = ApplicationProvider.getApplicationContext();
        Configuration cfg = new Configuration(base.getResources().getConfiguration());
        cfg.uiMode = (cfg.uiMode & ~Configuration.UI_MODE_NIGHT_MASK)
                | (night ? Configuration.UI_MODE_NIGHT_YES : Configuration.UI_MODE_NIGHT_NO);
        return base.createConfigurationContext(cfg);
    }

    private static float luminance(int color) {
        return (0.2126f * Color.red(color) + 0.7152f * Color.green(color) + 0.0722f * Color.blue(color)) / 255f;
    }

    @Test
    public void nightModeUsesDarkBackgroundAndLightText() {
        Context night = withNight(true);
        assertTrue(luminance(night.getColor(R.color.background)) < 0.2f);
        assertTrue(luminance(night.getColor(R.color.text_primary)) > 0.8f);
    }

    @Test
    public void dayModeUsesLightBackgroundAndDarkText() {
        Context day = withNight(false);
        assertTrue(luminance(day.getColor(R.color.background)) > 0.8f);
        assertTrue(luminance(day.getColor(R.color.text_primary)) < 0.2f);
    }
}
