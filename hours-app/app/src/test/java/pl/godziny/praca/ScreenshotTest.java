package pl.godziny.praca;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;

import androidx.test.core.app.ApplicationProvider;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

import java.io.File;
import java.io.FileOutputStream;
import java.util.TimeZone;

/**
 * Zrzut ekranu do przeglądu wyglądu (nie sprawdza niczego automatycznie): prawdziwy ekran
 * z przykładowym tygodniem i trwającą zmianą.
 * Uruchomienie: ./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'
 */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 34, qualifiers = "pl-rPL-w411dp-h891dp-xxhdpi")
public class ScreenshotTest {

    @Test public void mainScreen() throws Exception {
        Context ctx = ApplicationProvider.getApplicationContext();
        TimeZone tz = TimeZone.getDefault();
        long now = System.currentTimeMillis();
        long w = WorkMath.weekStart(now, java.util.Calendar.MONDAY, tz);
        EntryStore store = new EntryStore(ctx);
        long h = WorkMath.HOUR, m = WorkMath.MINUTE;
        // Kilka zmian z poprzednich dni tygodnia (o ile już minęły) i trwająca od 2 h 14 min.
        for (int d = 0; d < 4; d++) {
            long s = WorkMath.atTime(WorkMath.addDays(w, d, tz), 8, d * 5, tz);
            if (s + 9 * h < now - 3 * h) store.add(s, s + 8 * h + 30 * m + d * 7 * m);
        }
        store.add(now - 2 * h - 14 * m - 9_000, 0);

        MainActivity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        View root = a.findViewById(R.id.root);
        View content = ((android.view.ViewGroup) root).getChildAt(0);
        int width = root.getWidth();
        content.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
        content.layout(0, 0, width, content.getMeasuredHeight());

        Bitmap bmp = Bitmap.createBitmap(width, content.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bmp);
        canvas.drawColor(a.getColor(R.color.bg));
        content.draw(canvas);
        File dir = new File(System.getProperty("screenshots.dir", "screenshots"));
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        try (FileOutputStream out = new FileOutputStream(new File(dir, "godziny.png"))) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }
}
