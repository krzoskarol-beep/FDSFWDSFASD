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
 * z przykładowym tygodniem i trwającą zmianą, w motywie jasnym i ciemnym.
 * Uruchomienie: ./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'
 */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 34, qualifiers = "pl-rPL-w411dp-h891dp-xxhdpi")
public class ScreenshotTest {

    @Test public void mainScreen() throws Exception {
        render("godziny.png");
    }

    @Test @Config(qualifiers = "+night")
    public void mainScreenDark() throws Exception {
        render("godziny-ciemny.png");
    }

    @Test public void editDialog() throws Exception {
        renderDialog("edycja.png");
    }

    @Test @Config(qualifiers = "+night")
    public void editDialogDark() throws Exception {
        renderDialog("edycja-ciemny.png");
    }

    @Test public void settingsDialog() throws Exception {
        Context ctx = ApplicationProvider.getApplicationContext();
        MainActivity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        a.findViewById(R.id.rateBtn).performClick();
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
        saveDialog(a, org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog(), "ustawienia.png");
    }

    @Test public void deleteDay() throws Exception {
        Context ctx = ApplicationProvider.getApplicationContext();
        TimeZone tz = TimeZone.getDefault();
        long now = System.currentTimeMillis();
        long day = WorkMath.dayStart(now - 26 * WorkMath.HOUR, tz);
        EntryStore store = new EntryStore(ctx);
        store.add(day + 7 * WorkMath.HOUR, day + 11 * WorkMath.HOUR + 30 * WorkMath.MINUTE);
        store.add(day + 12 * WorkMath.HOUR, day + 16 * WorkMath.HOUR);
        MainActivity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        if (day < WorkMath.weekStart(now, java.util.Calendar.MONDAY, tz)) a.findViewById(R.id.prevWeek).performClick();
        android.view.ViewGroup list = a.findViewById(R.id.entryList);
        list.getChildAt(0).performClick();
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
        android.app.AlertDialog dlg = (android.app.AlertDialog) org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        saveDialog(a, dlg, "dzien.png");
        dlg.getButton(android.app.AlertDialog.BUTTON_POSITIVE).performClick();
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
        View panel = (View) a.findViewById(R.id.undoBar).getParent();
        int w = panel.getWidth();
        Bitmap bmp = Bitmap.createBitmap(w, panel.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(bmp);
        c.drawColor(a.getColor(R.color.bg));
        panel.draw(c);
        try (FileOutputStream out = new FileOutputStream(new File(
                System.getProperty("screenshots.dir", "screenshots"), "po-usunieciu.png"))) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }

    private void renderDialog(String fileName) throws Exception {
        Context ctx = ApplicationProvider.getApplicationContext();
        long now = System.currentTimeMillis();
        long s = now - now % WorkMath.MINUTE - 10 * WorkMath.HOUR;
        new EntryStore(ctx).add(s, s + 8 * WorkMath.HOUR + 30 * WorkMath.MINUTE);
        MainActivity a = Robolectric.buildActivity(MainActivity.class).setup().get();
        long week = WorkMath.weekStart(now, java.util.Calendar.MONDAY, TimeZone.getDefault());
        if (s < week) a.findViewById(R.id.prevWeek).performClick();
        ((android.view.ViewGroup) a.findViewById(R.id.entryList)).getChildAt(1).performClick();
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
        android.app.Dialog dlg = org.robolectric.shadows.ShadowAlertDialog.getLatestAlertDialog();
        dlg.findViewById(R.id.minus15).performClick();
        dlg.findViewById(R.id.break30).performClick();
        saveDialog(a, dlg, fileName);
    }

    private static void saveDialog(MainActivity a, android.app.Dialog dlg, String fileName) throws Exception {
        View d = dlg.getWindow().getDecorView();
        int w = a.findViewById(R.id.root).getWidth() * 88 / 100;
        d.measure(View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
        d.layout(0, 0, w, d.getMeasuredHeight());
        Bitmap bmp = Bitmap.createBitmap(w, d.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bmp);
        canvas.drawColor(a.getColor(R.color.bg));
        d.draw(canvas);
        File dir = new File(System.getProperty("screenshots.dir", "screenshots"));
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        try (FileOutputStream out = new FileOutputStream(new File(dir, fileName))) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }

    private void render(String fileName) throws Exception {
        Context ctx = ApplicationProvider.getApplicationContext();
        TimeZone tz = TimeZone.getDefault();
        long now = System.currentTimeMillis();
        long w = WorkMath.weekStart(now, java.util.Calendar.MONDAY, tz);
        EntryStore store = new EntryStore(ctx);
        long h = WorkMath.HOUR, m = WorkMath.MINUTE;
        // Kilka zmian z poprzednich dni tygodnia (o ile już minęły) i trwająca od 2 h 14 min.
        for (int d = 0; d < 4; d++) {
            long s = WorkMath.atTime(WorkMath.addDays(w, d, tz), 8, d * 5, tz);
            if (s + 9 * h < now - 3 * h) {
                Entry e = store.add(s, s + 8 * h + 30 * m + d * 7 * m);
                if (d == 1) store.update(e.withBreak(30));
                if (d == 2) store.update(e.withTimes(e.start - 12 * m, e.end));
            }
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
        try (FileOutputStream out = new FileOutputStream(new File(dir, fileName))) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }
}
