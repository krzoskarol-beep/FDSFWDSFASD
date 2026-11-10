#!/usr/bin/env python3
"""Szacunkowe obliczenia wytrzymałościowe dyszla i ramy (belkowo, ręcznie) dla v5 i v6.

Założenia (świadomie proste - to NIE zastępuje MES):
  * nacisk statyczny na hak z analiza_v*.json (motocykl 250 kg i 300 kg),
  * współczynnik dynamiczny pionowy 2,5 (nierówności drogi),
  * siła pozioma na zaczepie D = g*T*R/(T+R), T = 1500 kg (samochód), R = DMC przyczepy;
    działa na mimośrodzie e = 392 - 232 = 160 mm (kula wyżej niż oś dyszla D1) -> moment M_e,
  * dyszel D1 jako wspornik od kuli do pierwszej podpory (poprzeczka R5-1, X = 950),
    reakcje podpór liczone dla układu dwupodporowego: R5-1 i ostatnia podpora dyszla
    (v5: R5-4, X = 1806;  v6: poprzeczka osi R4, X = 2100),
  * poprzeczka jako belka swobodnie podparta na podłużnicach (rozpiętość 900 mm), siła w środku.
    python3 obliczenia.py wyniki/analiza_v5.json wyniki/analiza_v6.json wyniki/obliczenia.json
"""
import json
import sys

G = 9.81
KDYN = 2.5
T_AUTO = 1500.0
E_MIMO = 392.0 - 232.0
KULA_X = -75.0
X_R51 = 950.0
SPAN = 900.0


def W_rhs(b, h, t):
    """Wskaźnik wytrzymałości [mm3] rury prostokątnej b (szer.) x h (wys.) x t, zginanie w pionie."""
    return (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12.0 / (h / 2.0)


PROFILE = {
    'D1 100x40x4 płasko (v5/v6)': W_rhs(100, 40, 4),
    'D1 100x40x4 na sztorc': W_rhs(40, 100, 4),
    'D1 80x80x4': W_rhs(80, 80, 4),
    'R5 80x40x2': W_rhs(40, 80, 2),
    'R4/R2 120x50x2': W_rhs(50, 120, 2),
    'R2 120x50x3': W_rhs(50, 120, 3),
    'D2 60x60x4': W_rhs(60, 60, 4),
}


def case(hak_kg, dmc, x_last):
    T = KDYN * hak_kg * G                          # N
    D = G * T_AUTO * dmc / (T_AUTO + dmc)          # N
    Me = D * E_MIMO                                # Nmm
    a = X_R51 - KULA_X
    b = x_last - X_R51
    M_d1 = T * a + Me                              # moment w D1 nad R5-1
    R_front = T * (1 + a / b) + Me / b             # docisk do R5-1
    R_back = T * a / b + Me / b                    # odrywanie na ostatniej podporze
    out = {'T_dyn_N': round(T), 'D_N': round(D), 'M_e_Nm': round(Me / 1000), 'M_D1_Nm': round(M_d1 / 1000),
           'sigma_D1_plasko_MPa': round(M_d1 / PROFILE['D1 100x40x4 płasko (v5/v6)'], 0),
           'sigma_D1_sztorc_MPa': round(M_d1 / PROFILE['D1 100x40x4 na sztorc'], 0),
           'sigma_D1_80x80x4_MPa': round(M_d1 / PROFILE['D1 80x80x4'], 0),
           'R_R51_N': round(R_front), 'sigma_R51_MPa': round(R_front * SPAN / 4 / PROFILE['R5 80x40x2'], 0),
           'R_ostatnia_N': round(R_back),
           'D2_sigma_MPa': round(T * (150 - KULA_X) / PROFILE['D2 60x60x4'], 0)}
    return out


def main(a5, a6, out):
    R5, R6 = json.load(open(a5)), json.load(open(a6))
    res = {'profile_W_mm3': {k: round(v) for k, v in PROFILE.items()}, 'zalozenia': __doc__}
    for tag, R, x_last in (('v5', R5, 1806.0), ('v6', R6, 2100.0)):
        for row in R['nacisk_z_motocyklem']:
            if row['moto_kg'] in (250, 300):
                res[f"{tag}_moto{row['moto_kg']}"] = dict(hak_kg=row['hak_kg'], dmc=row['dmc'],
                                                         **case(row['hak_kg'], row['dmc'], x_last))
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k, v in res.items():
        if k != 'zalozenia':
            print(k, v)


if __name__ == '__main__':
    main(*sys.argv[1:4])
