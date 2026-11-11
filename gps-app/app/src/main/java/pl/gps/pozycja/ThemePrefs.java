package pl.gps.pozycja;

import android.content.Context;
import android.content.res.Configuration;

/**
 * Wybór motywu aplikacji: systemowy, jasny albo ciemny. Działa na każdym Androidzie od 7.0:
 * ekrany podmieniają tryb nocny w swojej konfiguracji w {@code attachBaseContext}, więc
 * zasoby z {@code values-night} wczytują się zgodnie z wyborem, a nie tylko z ustawieniem telefonu.
 */
final class ThemePrefs {

    static final int MODE_SYSTEM = 0;
    static final int MODE_LIGHT = 1;
    static final int MODE_DARK = 2;

    private static final String PREFS = "appearance";
    private static final String K_MODE = "themeMode";

    private ThemePrefs() { }

    static int get(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(K_MODE, MODE_SYSTEM);
    }

    static void set(Context c, int mode) {
        c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putInt(K_MODE, mode).apply();
    }

    /** Tryb UI z podmienionym bitem nocy według wyboru; pozostałe bity bez zmian. */
    static int uiModeFor(int mode, int currentUiMode) {
        int night;
        if (mode == MODE_DARK) night = Configuration.UI_MODE_NIGHT_YES;
        else if (mode == MODE_LIGHT) night = Configuration.UI_MODE_NIGHT_NO;
        else return currentUiMode;
        return (currentUiMode & ~Configuration.UI_MODE_NIGHT_MASK) | night;
    }

    /** Kontekst ekranu z wybranym motywem. Woła się z {@code attachBaseContext} każdej aktywności. */
    static Context wrap(Context base) {
        int mode = get(base);
        if (mode == MODE_SYSTEM) return base;
        Configuration cfg = new Configuration(base.getResources().getConfiguration());
        cfg.uiMode = uiModeFor(mode, cfg.uiMode);
        return base.createConfigurationContext(cfg);
    }
}
