package pl.gps.pozycja;

import android.bluetooth.BluetoothDevice;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.SystemClock;

/**
 * Połączenie z Bluetooth auta = początek jazdy, rozłączenie (wyłączenie silnika) = parking.
 * Te zdarzenia system dostarcza także zamkniętej aplikacji (są wyjątkiem od limitów Androida 8+).
 */
public class CarBluetoothReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        boolean connected = BluetoothDevice.ACTION_ACL_CONNECTED.equals(action);
        if (!connected && !BluetoothDevice.ACTION_ACL_DISCONNECTED.equals(action)) return;
        if (!CarBluetooth.isConfigured(context)) return;

        BluetoothDevice device = deviceFrom(intent);
        if (device == null || !CarBluetooth.addresses(context).contains(device.getAddress())) return;
        // Stan połączenia zapisujemy zawsze, żeby usługa wiedziała, czy jesteśmy w aucie.
        CarBluetooth.setConnected(context, device.getAddress(), connected);
        if (!AutoParking.isEnabled(context)) return;

        // Czas zdarzenia zapisujemy od razu: pozycję auta określa chwila rozłączenia, a nie późniejsza.
        long eventTime = SystemClock.elapsedRealtime();
        String name = CarBluetooth.nameFor(context, device.getAddress());

        if (connected) {
            EventLog.log(context, "Bluetooth: połączono z autem (" + name + ")");
            if (!DrivingService.start(context, DrivingService.ACTION_DRIVING_STARTED,
                    DrivingService.SOURCE_BLUETOOTH, eventTime)) {
                EventLog.log(context, "BŁĄD: system nie pozwolił uruchomić usługi jazdy");
                Notifications.showTrackingBlocked(context);
            }
        } else {
            EventLog.log(context, "Bluetooth: rozłączono z autem (" + name + ")");
            if (!DrivingService.start(context, DrivingService.ACTION_DRIVING_ENDED,
                    DrivingService.SOURCE_BLUETOOTH, eventTime)) {
                EventLog.log(context, "BŁĄD: system nie pozwolił uruchomić usługi, zapis awaryjny");
                Notifications.showTrackingBlocked(context);
                DrivingService.saveLastKnown(context, eventTime);
            }
        }
    }

    @SuppressWarnings("deprecation")
    private static BluetoothDevice deviceFrom(Intent intent) {
        return Build.VERSION.SDK_INT >= 33
                ? intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice.class)
                : intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
    }
}
