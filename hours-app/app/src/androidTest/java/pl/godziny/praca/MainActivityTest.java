package pl.godziny.praca;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

import android.content.Context;
import android.widget.Button;

import androidx.test.core.app.ActivityScenario;
import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Na urządzeniu: ekran się otwiera, Clock In zaczyna zmianę, a Clock Out ją kończy. */
@RunWith(AndroidJUnit4.class)
public class MainActivityTest {

    @Before public void clean() {
        Context ctx = ApplicationProvider.getApplicationContext();
        ctx.getSharedPreferences("godziny", Context.MODE_PRIVATE).edit().clear().commit();
    }

    @Test public void clockInAndOut() {
        Context ctx = ApplicationProvider.getApplicationContext();
        EntryStore store = new EntryStore(ctx);
        try (ActivityScenario<MainActivity> sc = ActivityScenario.launch(MainActivity.class)) {
            sc.onActivity(a -> {
                Button b = a.findViewById(R.id.clockBtn);
                assertEquals(a.getString(R.string.clock_in), b.getText().toString());
                b.performClick();
                assertNotNull(WorkMath.running(store.all()));
                assertEquals(a.getString(R.string.clock_out), b.getText().toString());
            });

            // Zmiana krótsza niż minuta jest odrzucana, więc cofnij jej początek o 2 h.
            Entry run = WorkMath.running(store.all());
            store.update(run.withTimes(run.start - 2 * WorkMath.HOUR, 0));

            sc.onActivity(a -> {
                Button b = a.findViewById(R.id.clockBtn);
                b.performClick();
                assertNull(WorkMath.running(store.all()));
                assertEquals(1, store.all().size());
                assertEquals(120, WorkMath.minutes(store.all().get(0), 0));
                assertEquals(a.getString(R.string.clock_in), b.getText().toString());
            });
        }
    }
}
