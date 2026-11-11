package pl.gps.pozycja;

import android.content.Context;
import android.graphics.Typeface;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

/**
 * Krój pisma aplikacji: Atkinson Hyperlegible (Braille Institute, licencja SIL OFL 1.1,
 * patrz gps-app/licenses). Zaprojektowany dla czytelności, także w pośpiechu i w nocy.
 * Ładowany z assets, więc działa na każdym Androidzie od 7.0.
 */
final class Fonts {

    private static Typeface regular, bold;

    private Fonts() { }

    private static void load(Context c) {
        if (regular != null) return;
        regular = Typeface.createFromAsset(c.getAssets(), "fonts/atkinson_regular.ttf");
        bold = Typeface.createFromAsset(c.getAssets(), "fonts/atkinson_bold.ttf");
    }

    /** Ustawia krój we wszystkich tekstach widoku, zachowując pogrubienia z layoutu. */
    static void apply(View root) {
        load(root.getContext());
        if (root instanceof TextView) {
            TextView t = (TextView) root;
            Typeface current = t.getTypeface();
            t.setTypeface(current != null && current.isBold() ? bold : regular);
        }
        if (root instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) root;
            for (int i = 0; i < g.getChildCount(); i++) apply(g.getChildAt(i));
        }
    }
}
