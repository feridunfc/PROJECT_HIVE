"""
PROJECT_HIVE Türkçe Komut Satırı Arayüzü
"""
import sys
import json
import asyncio
import aiohttp
import click
from typing import Optional, Dict, Any
from pathlib import Path
import time

# Yapılandırma
VARSayılan_API_URL = "http://localhost:8000"
VARSayılan_API_Anahtarı = "dev_key_123"


class HiveAPIClient:
    """PROJECT_HIVE API istemcisi."""

    def __init__(self, api_url: str = VARSayılan_API_URL, api_anahtari: str = VARSayılan_API_Anahtarı):
        self.api_url = api_url.rstrip('/')
        self.api_anahtari = api_anahtari
        self.headers = {
            "X-API-Key": api_anahtari,
            "Content-Type": "application/json"
        }

    async def pipeline_calistir(self, hedef: str, pipeline_tipi: str = "t1") -> Dict[str, Any]:
        """API üzerinden pipeline çalıştır."""
        url = f"{self.api_url}/api/v1/run"

        payload = {
            "goal": hedef,
            "pipeline_type": pipeline_tipi,
            "metadata": {
                "source": "cli_tr",
                "timestamp": time.time()
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API hatası {response.status}: {error_text}")

                return await response.json()

    async def gorev_durumu_al(self, gorev_id: str) -> Dict[str, Any]:
        """Görev durumunu al."""
        url = f"{self.api_url}/api/v1/tasks/{gorev_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API hatası {response.status}: {error_text}")

                return await response.json()

    async def gorev_sonucu_al(self, gorev_id: str) -> Dict[str, Any]:
        """Görev sonucunu al."""
        url = f"{self.api_url}/api/v1/tasks/{gorev_id}/result"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API hatası {response.status}: {error_text}")

                return await response.json()

    async def gorevleri_listele(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Görevleri listele."""
        url = f"{self.api_url}/api/v1/tasks?limit={limit}&offset={offset}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API hatası {response.status}: {error_text}")

                return await response.json()

    async def gorev_iptal_et(self, gorev_id: str) -> Dict[str, Any]:
        """Görevi iptal et."""
        url = f"{self.api_url}/api/v1/tasks/{gorev_id}/cancel"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API hatası {response.status}: {error_text}")

                return await response.json()

    async def saglik_kontrolu(self) -> Dict[str, Any]:
        """API sağlık kontrolü."""
        url = f"{self.api_url}/health"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()


@click.group()
@click.option('--api-url', default=VARSayılan_API_URL, help='API sunucu adresi')
@click.option('--api-anahtari', default=VARSayılan_API_Anahtarı, help='API anahtarı')
@click.pass_context
def cli(ctx, api_url, api_anahtari):
    """PROJECT_HIVE CLI - Çoklu Ajan Düzenleme Çerçevesi"""
    ctx.ensure_object(dict)
    ctx.obj['istemci'] = HiveAPIClient(api_url=api_url, api_anahtari=api_anahtari)


@cli.command()
@click.argument('hedef')
@click.option('--tip', '-t', 'pipeline_tipi',
              type=click.Choice(['t0', 't1'], case_sensitive=False),
              default='t1', help='Pipeline tipi (t0=hızlı, t1=güvenli)')
@click.option('--bekle', '-b', is_flag=True, help='Tamamlanmayı bekle')
@click.option('--zaman-asimi', default=300, help='Bekleme süresi (saniye)')
@click.option('--cikti', '-c', type=click.Path(), help='Sonuç çıktı dosyası')
@click.pass_context
def calistir(ctx, hedef, pipeline_tipi, bekle, zaman_asimi, cikti):
    """Verilen hedefle bir pipeline çalıştır."""
    istemci = ctx.obj['istemci']

    try:
        # Pipeline çalıştır
        click.echo(f"🚀 {pipeline_tipi.upper()} pipeline başlatılıyor...")
        click.echo(f"🎯 Hedef: {hedef}")

        sonuc = asyncio.run(istemci.pipeline_calistir(hedef, pipeline_tipi))
        gorev_id = sonuc['task_id']

        click.echo(f"✅ Görev gönderildi: {gorev_id}")
        click.echo(f"📊 Durum: {sonuc['status']}")
        click.echo(f"🔗 Kontrol URL: {ctx.obj['istemci'].api_url}/api/v1/tasks/{gorev_id}")

        if bekle:
            click.echo("\n⏳ Tamamlanması bekleniyor...")
            baslangic_zamani = time.time()

            while time.time() - baslangic_zamani < zaman_asimi:
                durum = asyncio.run(istemci.gorev_durumu_al(gorev_id))

                if durum['status'] in ['completed', 'failed', 'cancelled']:
                    click.echo(f"\n✅ Görev {durum['status']}!")

                    # Final sonucu al
                    sonuc = asyncio.run(istemci.gorev_sonucu_al(gorev_id))

                    if cikti:
                        with open(cikti, 'w', encoding='utf-8') as f:
                            json.dump(sonuc, f, indent=2, ensure_ascii=False)
                        click.echo(f"📁 Sonuç kaydedildi: {cikti}")
                    else:
                        click.echo(json.dumps(sonuc, indent=2, ensure_ascii=False))

                    return

                click.echo(f"⏳ Mevcut durum: {durum['status']}", nl=False)
                time.sleep(2)
                click.echo("\r", nl=False)

            click.echo(f"\n❌ {zaman_asimi} saniye sonra zaman aşımı")

        else:
            click.echo("\n💡 İpucu: İlerleme için `hive-tr durum <gorev_id>` kullanın")
            click.echo("💡 İpucu: Sonuç için `hive-tr sonuc <gorev_id>` kullanın")

    except Exception as e:
        click.echo(f"❌ Hata: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('gorev_id')
@click.pass_context
def durum(ctx, gorev_id):
    """Görev durumunu kontrol et."""
    istemci = ctx.obj['istemci']

    try:
        durum = asyncio.run(istemci.gorev_durumu_al(gorev_id))

        click.echo(f"📋 Görev: {gorev_id}")
        click.echo(f"🎯 Hedef: {durum['goal']}")
        click.echo(f"📊 Tip: {durum['pipeline_type'].upper()}")
        click.echo(f"🔧 Durum: {durum['status']}")
        click.echo(f"🕐 Oluşturulma: {durum['created_at']}")

        if durum.get('started_at'):
            click.echo(f"🚀 Başlangıç: {durum['started_at']}")

        if durum.get('completed_at'):
            click.echo(f"✅ Tamamlanma: {durum['completed_at']}")

            sure = "N/A"
            if durum['started_at'] and durum['completed_at']:
                from datetime import datetime
                baslangic = datetime.fromisoformat(durum['started_at'].replace('Z', '+00:00'))
                bitis = datetime.fromisoformat(durum['completed_at'].replace('Z', '+00:00'))
                sure = str(bitis - baslangic)

            click.echo(f"⏱️ Süre: {sure}")

        if durum.get('error'):
            click.echo(f"❌ Hata: {durum['error']}")

    except Exception as e:
        click.echo(f"❌ Hata: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('gorev_id')
@click.option('--cikti', '-c', type=click.Path(), help='Çıktı dosyası')
@click.pass_context
def sonuc(ctx, gorev_id, cikti):
    """Görev sonucunu al."""
    istemci = ctx.obj['istemci']

    try:
        sonuc = asyncio.run(istemci.gorev_sonucu_al(gorev_id))

        if cikti:
            with open(cikti, 'w', encoding='utf-8') as f:
                json.dump(sonuc, f, indent=2, ensure_ascii=False)
            click.echo(f"📁 Sonuç kaydedildi: {cikti}")
        else:
            click.echo(json.dumps(sonuc, indent=2, ensure_ascii=False))

    except Exception as e:
        click.echo(f"❌ Hata: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', default=10, help='Gösterilecek görev sayısı')
@click.option('--tum', '-t', 'tumunu_goster', is_flag=True, help='Tüm görevleri göster')
@click.pass_context
def liste(ctx, limit, tumunu_goster):
    """Son görevleri listele."""
    istemci = ctx.obj['istemci']

    try:
        if tumunu_goster:
            limit = 1000

        gorevler = asyncio.run(istemci.gorevleri_listele(limit=limit))

        if not gorevler.get('tasks'):
            click.echo("Görev bulunamadı")
            return

        click.echo(f"📋 Toplam {gorevler['total']} görev bulundu ({len(gorevler['tasks'])} gösteriliyor):")
        click.echo("")

        for gorev in gorevler['tasks']:
            durum_rengi = {
                'pending': '🟡',
                'running': '🟢',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '⭕'
            }.get(gorev['status'], '⚪')

            hedef_onizleme = gorev['goal']
            if len(hedef_onizleme) > 50:
                hedef_onizleme = hedef_onizleme[:47] + "..."

            click.echo(f"{durum_rengi} {gorev['task_id'][:8]}... | {gorev['pipeline_type'].upper():<4} | "
                       f"{gorev['status']:<10} | {hedef_onizleme}")

    except Exception as e:
        click.echo(f"❌ Hata: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('gorev_id')
@click.pass_context
def iptal(ctx, gorev_id):
    """Bekleyen bir görevi iptal et."""
    istemci = ctx.obj['istemci']

    try:
        sonuc = asyncio.run(istemci.gorev_iptal_et(gorev_id))
        click.echo(f"✅ {sonuc['message']}")

    except Exception as e:
        click.echo(f"❌ Hata: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def saglik(ctx):
    """API sağlık kontrolü."""
    istemci = ctx.obj['istemci']

    try:
        saglik = asyncio.run(istemci.saglik_kontrolu())

        if saglik['status'] == 'healthy':
            click.echo("✅ API sağlıklı")
            click.echo(f"📊 Sürüm: {saglik.get('version', 'N/A')}")

            if saglik.get('queue_stats'):
                istatistikler = saglik['queue_stats']
                click.echo(f"📈 Kuyruk: {istatistikler.get('pending', 0)} bekleyen, "
                           f"{istatistikler.get('running', 0)} çalışan, "
                           f"{istatistikler.get('completed', 0)} tamamlanan")
        else:
            click.echo(f"❌ API sağlıksız: {saglik}")

    except Exception as e:
        click.echo(f"❌ API bağlantı hatası: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Bağlanılacak host')
@click.option('--port', default=8000, help='Bağlanılacak port')
def sunucu(host, port):
    """API sunucusunu başlat."""
    import uvicorn

    click.echo(f"🚀 PROJECT_HIVE API sunucusu {host}:{port} üzerinde başlatılıyor")
    click.echo("📚 API dokümantasyonu: http://localhost:8000/docs")
    click.echo("📊 Kontrol Paneli: http://localhost:8000/dashboard")
    click.echo("📈 Metrikler: http://localhost:8000/metrics")
    click.echo("")
    click.echo("Durdurmak için Ctrl+C'ye basın")

    uvicorn.run(
        "interfaces.api.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=True
    )


if __name__ == "__main__":
    cli()