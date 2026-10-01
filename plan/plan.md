# DEADZONE: Repoyu Çalıştırma ve lastzhood.fun Yayını

Mevcut DEADZONE oyunu (tarayıcıda çalışan çok oyunculu 3D izometrik zombi oyunu) değiştirilmeden alınıp çalıştırılır ve yayına hazır hale getirilir.
Kod veya oyun mantığı değişmez. Yalnızca çalışması için gereken ayarlar yapılır ve ardından lastzhood.fun için yayın başlatılır.

## Kimler için
- lastzhood.fun'a girip oynayan oyuncular: masaüstünde WASD ve fare, mobilde dokunmatik kontroller.
- Admin panelinden bossları, gece/gündüz döngüsünü, zombi yoğunluğunu ve botları yöneten site sahibi.

## Temel özellikler ve deneyim (repodaki haliyle)
- Ana sayfa: harita arka planı ve ortada START GAME butonu. Sağ üstte CONNECT WALLET (RainbowKit, yalnız Robinhood Chain Mainnet 4663).
- Cüzdan girişi (SIWE). Her cüzdan bir kez $1 değerinde ETH ödeyerek oyuna erişim açar.
- Market: dört kutu paketi var, ödemeler aynı alıcı cüzdana gider.
- Oyun: oyuncu Glock 18 ile başlar. I tuşuyla 10 silahlık envanter açılır. Zombi türleri, bosslar, botlar, dost ateşi ve skor tablosu var.
- `/admin`: şifreyle girilen yönetim paneli.

## Kullanıcı akışı
1. Repo çekilir, bağımlılıklar kurulur, servisler çalıştırılır.
2. Gerekli ortam ayarları girilir. Reown Project ID, kullanıcının sohbete yazacağı değerle eklenir.
3. Ana sayfanın açıldığı ve API'nin yanıt verdiği yalnızca göz ucuyla kontrol edilir. Test turu yapılmaz.
4. Bunun hemen ardından lastzhood.fun için yayın (deploy) başlatılır.

## UI/UX hissi
Repodaki tasarım olduğu gibi korunur: koyu, taktik ve hayatta kalma temalı arayüz, Bebas ve Barlow yazı tipleri. Görsel bir değişiklik yapılmaz.

## Uygulama aşamaları
- **Aşama 1 (şimdi):** Repoyu çekme, bağımlılıkları kurma, ortam ayarlarını yapma, çalıştırma ve yayını başlatma.
- **Aşama 2 (sonra):** lastzhood.fun alan adının bağlanması ve canlıda $1 erişim tanınmasının kontrolü. Bu kontrol, kullanıcının gerçek cüzdanıyla yapılır.
- **Aşama 3 (sonra):** Admin şifresinin güçlü bir şifreyle değiştirilmesi, 200 oyunculuk yük testi ve kullanıcı isteğine göre yeni geliştirmeler.

## Varsayımlar
- Hiçbir test turu yapılmaz. Bunu kullanıcı açıkça istedi. Yalnızca uygulamanın açıldığına bakılır.
- Ödeme alıcı cüzdanı `0x45d9AA6ef98407dda4911c6f4a9Af59f3de4E334` olarak kalır.
- Admin şifresi şimdilik `123123` olarak kalır. Zayıf ve geçici bir şifredir.
- Reown Project ID'yi kullanıcı sohbete yazacak. Bu değer gelmezse cüzdan bağlantısı (WalletConnect/QR) çalışmaz.
- Ağ yalnız Robinhood Chain Mainnet 4663'tür. RPC adresi, ETH/USD fiyat kaynağı ve MetaMask bağlantıları repodaki PRD'de yazan değerlerle kurulur.
- Yönetici oturumu ve cüzdan girişi için izin verilen adresler hem önizleme hem lastzhood.fun alan adını kapsayacak şekilde ayarlanır.
- Repodaki kod, oyun dengesi ve görseller değiştirilmez. Kurulum sırasında engelleyici bir hata çıkarsa yalnızca uygulamanın çalışması için gereken en küçük düzeltme yapılır.
- Önceki canlı veriler (oyuncu kayıtları, erişim ödemeleri) taşınmaz. Yeni yayın kendi veritabanıyla başlar.
