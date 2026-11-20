package pl.pozycja.polska;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import android.Manifest;
import android.content.Context;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Looper;
import android.os.Build;
import android.os.ParcelFileDescriptor;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.rule.GrantPermissionRule;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Prawdziwa podmiana pozycji na urządzeniu: zgoda „aplikacja do pozorowania lokalizacji”
 * jest nadawana poleceniem appops (jak wybór w Opcjach programisty), a system musi potem
 * zwracać pozycję w Warszawie oznaczoną jako pozorowana.
 */
@RunWith(AndroidJUnit4.class)
public class MockEngineTest {

    @Rule public GrantPermissionRule location =
            GrantPermissionRule.grant(Manifest.permission.ACCESS_FINE_LOCATION);

    private final Context ctx = InstrumentationRegistry.getInstrumentation().getTargetContext();
    private MockEngine engine;

    @Before public void setUp() throws IOException {
        shell("cmd location set-location-enabled true");
        engine = new MockEngine(ctx);
    }

    @After public void tearDown() throws IOException {
        engine.stop();
        shell("appops set " + ctx.getPackageName() + " android:mock_location default");
    }

    @Test public void refusedWithoutDeveloperOptionChoice() throws IOException {
        shell("appops set " + ctx.getPackageName() + " android:mock_location deny");
        assertFalse(MockEngine.isAllowed(ctx));
        try {
            engine.start();
            fail("bez zgody start powinien rzucić SecurityException");
        } catch (SecurityException expected) {
            assertFalse(engine.isStarted());
        }
    }

    /**
     * Pozycję odczytujemy tak jak inne aplikacje: nasłuchując dostawcy GPS przy otwartym
     * ekranie. Android 10+ nie podaje pozycji procesowi w tle bez uprawnienia „zawsze”,
     * więc ekran aplikacji musi być na wierzchu (jak przy przycisku „Sprawdź”).
     */
    @SuppressWarnings("MissingPermission")
    @Test public void systemReportsWarsaw() throws Exception {
        shell("appops set " + ctx.getPackageName() + " android:mock_location allow");
        assertTrue(MockEngine.isAllowed(ctx));

        try (ActivityScenario<MainActivity> ignored = ActivityScenario.launch(MainActivity.class)) {
            engine.start();
            assertTrue(engine.isStarted());
            Places.Place w = Places.byName("Warszawa");

            LocationManager lm = ctx.getSystemService(LocationManager.class);
            AtomicReference<Location> got = new AtomicReference<>();
            CountDownLatch latch = new CountDownLatch(1);
            LocationListener listener = new LocationListener() {
                @Override public void onLocationChanged(Location l) {
                    got.compareAndSet(null, l);
                    latch.countDown();
                }
                @Override public void onStatusChanged(String p, int s, Bundle b) { }
                @Override public void onProviderEnabled(String p) { }
                @Override public void onProviderDisabled(String p) { }
            };
            lm.requestLocationUpdates(LocationManager.GPS_PROVIDER, 0L, 0f, listener,
                    Looper.getMainLooper());
            try {
                // Jak usługa: wysyłamy pozycję co chwilę, aż system ją dostarczy.
                for (int i = 0; i < 20 && latch.getCount() > 0; i++) {
                    engine.push(w.lat, w.lon, 4f);
                    latch.await(500, TimeUnit.MILLISECONDS);
                }
            } finally {
                lm.removeUpdates(listener);
            }

            Location l = got.get();
            assertNotNull("system nie dostarczył pozycji GPS", l);
            assertEquals(w.lat, l.getLatitude(), 1e-6);
            assertEquals(w.lon, l.getLongitude(), 1e-6);
            assertTrue(Coords.inPoland(l.getLatitude(), l.getLongitude()));
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                assertTrue(l.isMock());
            } else {
                //noinspection deprecation
                assertTrue(l.isFromMockProvider());
            }

            engine.stop();
            assertFalse(engine.isStarted());
        }
    }

    private static void shell(String cmd) throws IOException {
        ParcelFileDescriptor pfd = InstrumentationRegistry.getInstrumentation()
                .getUiAutomation().executeShellCommand(cmd);
        try (InputStream in = new FileInputStream(pfd.getFileDescriptor())) {
            byte[] buf = new byte[1024];
            //noinspection StatementWithEmptyBody
            while (in.read(buf) != -1) { } // czekamy na zakończenie polecenia
        } finally {
            pfd.close();
        }
    }
}
