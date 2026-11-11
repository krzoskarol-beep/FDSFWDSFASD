package pl.korektor.dzwiek;

import static org.junit.Assert.assertNotNull;

import android.app.Activity;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Dymny test na urządzeniu: ekran otwiera się bez błędu nawet tam, gdzie globalny
 * korektor nie jest dostępny (np. emulator) — wtedy pokazuje komunikat, nie wyjątek.
 */
@RunWith(AndroidJUnit4.class)
public class EqActivitySmokeTest {

    @Test public void launchesWithoutCrash() {
        try (ActivityScenario<EqActivity> scenario = ActivityScenario.launch(EqActivity.class)) {
            scenario.onActivity(a -> assertNotNull(a.findViewById(R.id.master)));
        }
    }
}
