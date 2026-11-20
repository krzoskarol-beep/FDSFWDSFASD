package pl.pozycja.polska;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

import android.view.View;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Test;
import org.junit.runner.RunWith;

/** Ekran otwiera się bez błędu i pokazuje wszystkie miasta. */
@RunWith(AndroidJUnit4.class)
public class AppSmokeTest {

    @Test public void launchesWithoutCrash() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(a -> {
                assertNotNull(a.findViewById(R.id.toggle));
                android.widget.LinearLayout grid = a.findViewById(R.id.placeGrid);
                int chips = 0;
                for (int i = 0; i < grid.getChildCount(); i++) {
                    chips += ((android.view.ViewGroup) grid.getChildAt(i)).getChildCount();
                }
                assertEquals(Places.ALL.length, chips);
                assertEquals(View.VISIBLE, a.findViewById(R.id.statusPanel).getVisibility());
            });
        }
    }
}
