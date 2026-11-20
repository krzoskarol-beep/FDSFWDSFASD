package pl.pozycja.polska;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;

import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

import java.io.File;
import java.io.FileOutputStream;

/**
 * Zrzuty ekranu do przeglądu wyglądu (nie sprawdzają niczego automatycznie).
 * Uruchomienie: ./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'
 */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 34, qualifiers = "pl-rPL-w411dp-h891dp-xxhdpi")
public class ScreenshotTest {

    @After public void reset() {
        MockService.running = false;
    }

    @Test public void offWithSetup() throws Exception {
        MockService.running = false;
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        a.findViewById(R.id.setupPanel).setVisibility(View.VISIBLE);
        save(a, "wylaczone.png");
    }

    @Test public void on() throws Exception {
        MockService.running = true;
        Activity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        save(a, "wlaczone.png");
    }

    private static void save(Activity a, String file) throws Exception {
        View root = ((android.view.ViewGroup) a.findViewById(R.id.scroll)).getChildAt(0);
        int width = root.getWidth() > 0 ? root.getWidth()
                : Math.round(411 * a.getResources().getDisplayMetrics().density);
        root.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
        root.layout(0, 0, width, root.getMeasuredHeight());
        Bitmap bmp = Bitmap.createBitmap(root.getWidth(), root.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bmp);
        canvas.drawColor(a.getColor(R.color.bg));
        root.draw(canvas);
        File dir = new File(System.getProperty("screenshots.dir", "screenshots"));
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        try (FileOutputStream out = new FileOutputStream(new File(dir, file))) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }
}
