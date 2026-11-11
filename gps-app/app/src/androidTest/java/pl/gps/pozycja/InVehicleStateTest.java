package pl.gps.pozycja;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Stan „w pojeździe” z rozpoznawania aktywności, z którego korzysta DrivePolicy. */
@RunWith(AndroidJUnit4.class)
public class InVehicleStateTest {

    private final Context context = ApplicationProvider.getApplicationContext();

    @After
    public void tearDown() {
        AutoParking.clearInVehicle(context);
    }

    @Test
    public void enterAndExitOfVehicle() {
        AutoParking.clearInVehicle(context);
        assertFalse(AutoParking.isInVehicle(context));
        AutoParking.setInVehicle(context, true);
        assertTrue(AutoParking.isInVehicle(context));
        AutoParking.setInVehicle(context, false);
        assertFalse(AutoParking.isInVehicle(context));
    }

    @Test
    public void clearedAfterReboot() {
        AutoParking.setInVehicle(context, true);
        AutoParking.clearInVehicle(context);
        assertFalse(AutoParking.isInVehicle(context));
    }

    @Test
    public void disablingAutoSavingForgetsState() {
        AutoParking.setInVehicle(context, true);
        AutoParking.disable(context);
        assertFalse(AutoParking.isInVehicle(context));
        assertFalse(AutoParking.isEnabled(context));
    }
}
