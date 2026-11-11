package pl.gps.pozycja;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Po restarcie telefonu i aktualizacji aplikacji sprawdza, czy automatyczny zapis
 * nadal ma potrzebne uprawnienia (wpis do dziennika diagnostycznego).
 */
public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String a = intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(a) || Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)) {
            EventLog.log(context, Intent.ACTION_BOOT_COMPLETED.equals(a)
                    ? "Restart telefonu" : "Aktualizacja aplikacji");
            AutoParking.checkAfterBoot(context);
        }
    }
}
