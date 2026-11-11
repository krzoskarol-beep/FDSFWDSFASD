package pl.gps.pozycja;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.util.HashMap;
import java.util.Map;

@RunWith(AndroidJUnit4.class)
public class CarBluetoothStateTest {

    private static final String CAR = "00:11:22:33:44:55";
    private static final String HEADPHONES = "AA:BB:CC:DD:EE:FF";
    private final Context context = ApplicationProvider.getApplicationContext();

    @Before
    public void setUp() {
        Map<String, String> selected = new HashMap<>();
        selected.put(CAR, "Moje auto");
        CarBluetooth.save(context, selected);
        CarBluetooth.clearConnected(context);
    }

    @After
    public void tearDown() {
        CarBluetooth.save(context, new HashMap<>());
        CarBluetooth.clearConnected(context);
    }

    @Test
    public void connectAndDisconnectOfCar() {
        assertFalse(CarBluetooth.isCarConnected(context));
        CarBluetooth.setConnected(context, CAR, true);
        assertTrue(CarBluetooth.isCarConnected(context));
        CarBluetooth.setConnected(context, CAR, false);
        assertFalse(CarBluetooth.isCarConnected(context));
    }

    @Test
    public void otherDevicesDoNotCountAsCar() {
        CarBluetooth.setConnected(context, HEADPHONES, true);
        assertFalse(CarBluetooth.isCarConnected(context));
    }

    @Test
    public void deselectingCarWhileConnected() {
        CarBluetooth.setConnected(context, CAR, true);
        CarBluetooth.save(context, new HashMap<>());
        assertFalse(CarBluetooth.isCarConnected(context));
    }

    @Test
    public void clearAfterReboot() {
        CarBluetooth.setConnected(context, CAR, true);
        CarBluetooth.clearConnected(context);
        assertFalse(CarBluetooth.isCarConnected(context));
    }
}
