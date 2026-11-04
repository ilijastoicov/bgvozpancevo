# BG voz obaveštenja – Pančevo ⇄ Zemun

Na svakih 10 minuta proverava „Informacije uživo“ na sajtu Srbijavoza i šalje
Telegram poruku kad se pojavi obaveštenje koje pominje Pančevo, Pančevo
Vojlovicu ili Vršac (vozovi Vršac–Zemun idu kroz Pančevo), kao i kad se
obustavlja ceo saobraćaj. Obaveštenja koja pominju samo Pančevački most se
preskaču, jer se tiču drugih linija.

## 1. Napravi Telegram bota (2 minuta)

1. U Telegramu otvori **@BotFather** i pošalji `/newbot`.
2. Unesi ime (npr. *BG voz Pančevo*) i korisničko ime koje se završava na `bot`.
3. BotFather ti vraća **token** u obliku `123456789:AA...`. Sačuvaj ga.
4. Otvori svog novog bota i pošalji mu bilo koju poruku (npr. „zdravo“).
5. U pretraživaču otvori
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (umesto `<TOKEN>` stavi svoj token) i pronađi `"chat":{"id":123456789`.
   Taj broj je tvoj **chat ID**.

## 2. Napravi GitHub repozitorijum

1. Na GitHubu napravi novi repozitorijum, npr. `bgvoz-alert`.
   - **Public** je preporučen: Actions su tada potpuno besplatni i neograničeni.
     U kodu nema ništa tajno, token stoji u Secrets.
   - **Private** daje samo 2.000 besplatnih minuta mesečno, a provera na
     10 minuta troši oko 4.300. Zato repo mora biti javni, ili u `notify.yml`
     promeni `*/10 * * * *` u `*/30 * * * *`.
2. Dodaj `bg_voz_notify.py` i `README.md`: **Add file → Upload files**.
3. Workflow dodaj ručno, jer se skriveni folder `.github` lako preskoči pri
   prevlačenju: **Add file → Create new file**, za ime upiši
   `.github/workflows/notify.yml` i nalepi sadržaj fajla `notify.yml`.

## 3. Unesi tajne

**Settings → Secrets and variables → Actions → New repository secret**:

| Ime                  | Vrednost              |
|----------------------|-----------------------|
| `TELEGRAM_BOT_TOKEN` | token od BotFathera   |
| `TELEGRAM_CHAT_ID`   | broj iz `getUpdates`  |

## 4. Prvo pokretanje

**Actions → BG voz obaveštenja → Run workflow**.

Pri prvom pokretanju dobićeš sva relevantna obaveštenja iz poslednja 24 sata,
pa odmah vidiš da li sve radi. Posle toga stižu samo nova. U logu koraka
„Proveri obaveštenja“ piše koliko je obaveštenja preuzeto i koliko je novih.

## Podešavanja (opciono)

- **Druge ključne reči** bez menjanja koda: Settings → Secrets and variables →
  Actions → **Variables** → `KEYWORDS_REGEX`. Tekst se pre poređenja svodi na
  mala slova, latinicu i bez kvačica (š → s, č → c, đ → dj). Primer koji
  dodaje i Ovču: `\bpancev(o|a|u|om)\b|vojlovic|\bvrs(ac|ca|cu)\b|\bovc(a|e|u)\b`
- **Lokalna proba** bez slanja poruka: `python bg_voz_notify.py --dry-run`

## Dobro je znati

- GitHub zakazana pokretanja ponekad kasne 5–15 minuta, naročito u punom satu.
- Ako repo 60 dana nema nikakvu aktivnost, GitHub isključi zakazani workflow i
  pošalje ti mejl. Ponovo ga uključiš jednim klikom u kartici Actions. Svako
  poslato obaveštenje upisuje `seen.json`, što se računa kao aktivnost.
- Ako Srbijavoz promeni izvor podataka, u logu će pisati „ne mogu da preuzmem
  obaveštenja“. Tada treba ažurirati `API_URL` u skripti.
