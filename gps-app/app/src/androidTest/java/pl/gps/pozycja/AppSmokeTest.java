package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import android.Manifest;
import android.content.Context;
import android.view.View;
import android.widget.TextView;

import androidx.test.core.app.ActivityScenario;
import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.rule.GrantPermissionRule;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Uruchamia prawdziwe ekrany aplikacji na emulatorze i sprawdza, że się nie wysypują. */
@RunWith(AndroidJUnit4.class)
public class AppSmokeTest {

    @Rule
    public GrantPermissionRule permissions = GrantPermissionRule.grant(
            Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION);

    private final Context context = ApplicationProvider.getApplicationContext();

    @Before
    public void setUp() {
        new ParkingStore(context).clear();
        EventLog.clear(context);
    }

    @Test
    public void mainScreenWithoutParkingShowsSaveButton() {
        try (ActivityScenario<MainActivity> s = ActivityScenario.launch(MainActivity.class)) {
            s.onActivity(a -> {
                assertEquals(View.VISIBLE, a.findViewById(R.id.parkingEmpty).getVisibility());
                assertEquals(View.GONE, a.findViewById(R.id.parkingSaved).getVisibility());
            });
        }
    }

    @Test
    public void mainScreenShowsSavedParking() {
        new ParkingStore(context).save(new ParkingStore.Spot(52.2318, 21.006, 8f,
                System.currentTimeMillis() - 5 * 60_000L, "poziom -2"));
        try (ActivityScenario<MainActivity> s = ActivityScenario.launch(MainActivity.class)) {
            s.onActivity(a -> {
                assertEquals(View.VISIBLE, a.findViewById(R.id.parkingSaved).getVisibility());
                TextView note = a.findViewById(R.id.parkingNote);
                assertEquals("poziom -2", note.getText().toString());
                TextView savedAt = a.findViewById(R.id.parkingSavedAt);
                assertTrue(savedAt.getText().toString(), savedAt.getText().toString().contains("5 min"));
            });
        }
    }

    @Test
    public void backgroundSaveUpdatesStoreAndLog() {
        ParkingDetector.Fix fix = new ParkingDetector.Fix(50.0614, 19.9366, 6f, 0f,
                android.os.SystemClock.elapsedRealtime());
        DrivingService.saveParking(context, fix, false);

        ParkingStore.Spot spot = new ParkingStore(context).load();
        assertNotNull(spot);
        assertEquals(50.0614, spot.latitude, 1e-9);
        assertEquals(context.getString(R.string.auto_note), spot.note);
        assertTrue(EventLog.read(context).get(0).contains("ZAPISANO"));
    }

    @Test
    public void diagnosticsScreenShowsStatus() {
        EventLog.log(context, "test diagnostyki");
        try (ActivityScenario<DiagnosticsActivity> s = ActivityScenario.launch(DiagnosticsActivity.class)) {
            s.onActivity(a -> {
                String status = ((TextView) a.findViewById(R.id.diagStatus)).getText().toString();
                assertTrue(status, status.contains("Lokalizacja dokładna: tak"));
                String log = ((TextView) a.findViewById(R.id.diagLog)).getText().toString();
                assertTrue(log, log.contains("test diagnostyki"));
            });
        }
    }
}
