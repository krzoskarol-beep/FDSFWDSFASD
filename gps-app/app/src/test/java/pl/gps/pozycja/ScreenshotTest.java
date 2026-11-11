package pl.gps.pozycja;

import android.content.Context;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;

import androidx.test.core.app.ActivityScenario;
import androidx.test.core.app.ApplicationProvider;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.Shadows;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

import java.io.File;
import java.io.FileOutputStream;

/**
 * Zrzuty ekranów do przeglądu wyglądu (nie sprawdzają niczego automatycznie).
 * Uruchomienie: ./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'
 * Pliki PNG trafiają do gps-app/screenshots/.
 */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = 34, qualifiers = "pl-rPL-w411dp-h891dp-xxhdpi")
public class ScreenshotTest {

    private final Context context = ApplicationProvider.getApplicationContext();

    private static void save(View root, String name) throws Exception {
        int w = root.getWidth(), h = root.getHeight();
        Bitmap b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(b);
        canvas.drawColor(root.getContext().getColor(R.color.background)); // tło okna
        root.draw(canvas);
        File dir = new File(System.getProperty("screenshots.dir", "screenshots"));
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        try (FileOutputStream out = new FileOutputStream(new File(dir, name + ".png"))) {
            b.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }

    private void shoot(String name, boolean dark, boolean withSpot) throws Exception {
        ThemePrefs.set(context, dark ? ThemePrefs.MODE_DARK : ThemePrefs.MODE_LIGHT);
        ParkingStore store = new ParkingStore(context);
        store.clear();
        if (withSpot) {
            store.save(new ParkingStore.Spot(52.2318, 21.0060, 6f,
                    System.currentTimeMillis() - 47 * 60_000L, "Poziom -2, sektor B",
                    "Marszałkowska 10, Warszawa"));
        }
        // Realistyczny stan: dostęp do lokalizacji i świeży pomiar GPS ok. 350 m od auta.
        Shadows.shadowOf((android.app.Application) context).grantPermissions(
                android.Manifest.permission.ACCESS_FINE_LOCATION,
                android.Manifest.permission.ACCESS_COARSE_LOCATION);
        android.location.LocationManager lm = context.getSystemService(android.location.LocationManager.class);
        Shadows.shadowOf(lm).setProviderEnabled(android.location.LocationManager.GPS_PROVIDER, true);
        android.location.Location here = new android.location.Location(android.location.LocationManager.GPS_PROVIDER);
        here.setLatitude(52.22905);
        here.setLongitude(21.00915);
        here.setAccuracy(4f);
        here.setAltitude(112);
        here.setSpeed(0.4f);
        here.setTime(System.currentTimeMillis());
        here.setElapsedRealtimeNanos(android.os.SystemClock.elapsedRealtimeNanos());
        Shadows.shadowOf(lm).setLastKnownLocation(android.location.LocationManager.GPS_PROVIDER, here);
        Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
        try (ActivityScenario<MainActivity> s = ActivityScenario.launch(MainActivity.class)) {
            // Pomiar GPS dociera do ekranu tak jak na telefonie: przez jego nasłuch lokalizacji.
            // (Ekran ma własny kontekst z wybranym motywem, a w Robolectric także własny,
            // symulowany LocationManager, więc pomiar wysyłamy właśnie do niego.)
            s.onActivity(a -> {
                android.location.LocationManager screenLm = a.getSystemService(android.location.LocationManager.class);
                Shadows.shadowOf(screenLm).setProviderEnabled(android.location.LocationManager.GPS_PROVIDER, true);
                here.setElapsedRealtimeNanos(android.os.SystemClock.elapsedRealtimeNanos());
                Shadows.shadowOf(screenLm).simulateLocation(here);
            });
            Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
            s.onActivity(a -> {
                View root = a.findViewById(R.id.root);
                // Cała przewijana treść, nie tylko widoczny fragment ekranu.
                View content = ((android.view.ViewGroup) root).getChildAt(0);
                int width = a.getWindow().getDecorView().getWidth();
                content.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
                content.layout(0, 0, content.getMeasuredWidth(), content.getMeasuredHeight());
                try {
                    save(content, name);
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
            });
        }
    }

    private <T extends android.app.Activity> void shootActivity(Class<T> cls, String name, boolean dark)
            throws Exception {
        ThemePrefs.set(context, dark ? ThemePrefs.MODE_DARK : ThemePrefs.MODE_LIGHT);
        try (ActivityScenario<T> s = ActivityScenario.launch(cls)) {
            s.onActivity(a -> {
                View root = a.findViewById(R.id.root);
                int width = a.getWindow().getDecorView().getWidth();
                int height = a.getWindow().getDecorView().getHeight();
                root.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY));
                root.layout(0, 0, width, height);
                try {
                    save(root, name);
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
            });
        }
    }

    @Test
    public void historyLight() throws Exception {
        ParkingStore store = new ParkingStore(context);
        store.clearHistory();
        long now = System.currentTimeMillis();
        store.save(new ParkingStore.Spot(50.0614, 19.9366, 8f, now - 3 * 86_400_000L, "", "Floriańska 12, Kraków"));
        store.save(new ParkingStore.Spot(52.2318, 21.0060, 6f, now - 47 * 60_000L,
                "Poziom -2, sektor B", "Marszałkowska 10, Warszawa"));
        shootActivity(HistoryActivity.class, "history_light", false);
    }

    @Test
    public void diagnosticsDark() throws Exception {
        EventLog.clear(context);
        EventLog.log(context, "Usługi Google: W POJEŹDZIE (zdarzenie sprzed 4 s)");
        EventLog.log(context, "GPS potwierdza jazdę (47 km/h)");
        EventLog.log(context, "ZAPISANO parking: 52.231800, 21.006000");
        shootActivity(DiagnosticsActivity.class, "diagnostics_dark", true);
    }

    @Test
    public void mainLightWithParking() throws Exception {
        shoot("main_light_parking", false, true);
    }

    @Test
    public void mainDarkWithParking() throws Exception {
        shoot("main_dark_parking", true, true);
    }

    @Test
    public void mainLightEmpty() throws Exception {
        shoot("main_light_empty", false, false);
    }

    @Test
    public void mainDarkEmpty() throws Exception {
        shoot("main_dark_empty", true, false);
    }
}
