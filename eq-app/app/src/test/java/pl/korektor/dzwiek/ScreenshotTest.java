package pl.korektor.dzwiek;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.TextView;

import androidx.test.core.app.ApplicationProvider;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

import java.io.File;
import java.io.FileOutputStream;

/**
 * Zrzut ekranu do przeglądu wyglądu (nie sprawdza niczego automatycznie). Inflatuje
 * prawdziwy układ i wypełnia go przykładowymi pasmami, więc pokazuje realny wygląd
 * nawet tam, gdzie silnik efektów nie jest dostępny.
 * Uruchomienie: ./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'
 */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 34, qualifiers = "pl-rPL-w411dp-h891dp-xxhdpi")
public class ScreenshotTest {

    private final Context base = ApplicationProvider.getApplicationContext();

    private static final int MIN = -1500, MAX = 1500;
    private static final String[] FREQ = {"60 Hz", "230 Hz", "910 Hz", "3.6 kHz", "14 kHz"};
    private static final short[] LEVELS = {600, 300, 0, 200, 500};
    private static final String[] PRESETS = {"Normalny", "Rock", "Pop", "Jazz", "Klasyka", "Własny"};

    @Test public void equalizer() throws Exception {
        Context ctx = new android.view.ContextThemeWrapper(base, R.style.AppTheme);
        View root = LayoutInflater.from(ctx).inflate(R.layout.activity_eq, null, false);

        ((android.widget.Switch) root.findViewById(R.id.master)).setChecked(true);
        root.findViewById(R.id.statusMsg).setVisibility(View.GONE);

        // Zestawy (ostatni „Własny” zaznaczony)
        LinearLayout presetRow = root.findViewById(R.id.presetRow);
        for (int i = 0; i < PRESETS.length; i++) {
            Button chip = new Button(ctx);
            chip.setText(PRESETS[i]);
            chip.setAllCaps(false);
            chip.setTextSize(14f);
            chip.setBackgroundResource(R.drawable.chip_bg);
            chip.setTextColor(ctx.getColorStateList(R.color.chip_text));
            chip.setStateListAnimator(null);
            chip.setPadding(dp(ctx, 18), 0, dp(ctx, 18), 0);
            chip.setSelected(i == PRESETS.length - 1);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT, dp(ctx, 40));
            lp.rightMargin = dp(ctx, 8);
            chip.setLayoutParams(lp);
            presetRow.addView(chip);
        }

        // Fadery
        LinearLayout faderRow = root.findViewById(R.id.faderRow);
        for (int b = 0; b < FREQ.length; b++) {
            LinearLayout col = new LinearLayout(ctx);
            col.setOrientation(LinearLayout.VERTICAL);
            col.setGravity(Gravity.CENTER_HORIZONTAL);
            col.setLayoutParams(new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.MATCH_PARENT, 1f));

            TextView db = new TextView(ctx);
            db.setText(EqMath.formatDb(LEVELS[b]));
            db.setTextColor(ctx.getColor(R.color.text_dim));
            db.setTextSize(11f);
            db.setGravity(Gravity.CENTER);
            db.setTypeface(Typeface.MONOSPACE);
            col.addView(db, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

            FaderView fader = new FaderView(ctx, null);
            fader.setFraction(EqMath.levelToFraction(LEVELS[b], (short) MIN, (short) MAX));
            LinearLayout.LayoutParams fLp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
            fLp.topMargin = dp(ctx, 6);
            fLp.bottomMargin = dp(ctx, 6);
            col.addView(fader, fLp);

            TextView freq = new TextView(ctx);
            freq.setText(FREQ[b]);
            freq.setTextColor(ctx.getColor(R.color.text_dim));
            freq.setTextSize(11f);
            freq.setGravity(Gravity.CENTER);
            freq.setTypeface(Typeface.MONOSPACE);
            col.addView(freq, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

            faderRow.addView(col);
        }

        ((SeekBar) root.findViewById(R.id.bass)).setProgress(620);
        ((SeekBar) root.findViewById(R.id.surround)).setProgress(300);

        int width = dp(ctx, 411);
        root.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
        root.layout(0, 0, width, root.getMeasuredHeight());

        save(root, ctx);
    }

    private static void save(View root, Context ctx) throws Exception {
        Bitmap bmp = Bitmap.createBitmap(root.getWidth(), root.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bmp);
        canvas.drawColor(ctx.getColor(R.color.bg));
        root.draw(canvas);
        File dir = new File(System.getProperty("screenshots.dir", "screenshots"));
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        try (FileOutputStream out = new FileOutputStream(new File(dir, "korektor.png"))) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }

    private static int dp(Context ctx, int v) {
        return Math.round(v * ctx.getResources().getDisplayMetrics().density);
    }
}
