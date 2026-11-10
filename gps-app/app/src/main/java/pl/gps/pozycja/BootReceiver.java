package pl.gps.pozycja;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Usługi Google zapominają rejestrację wykrywania jazdy po restarcie telefonu
 * i po aktualizacji aplikacji, więc odnawiamy ją w tych momentach.
 */
public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String a = intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(a) || Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)) {
            AutoParking.reRegisterIfEnabled(context);
        }
    }
}
