API v2 rajapinta
Huomaa: Tämä on uusi suositeltu v2 rajapinta. Vanha v1 rajapinta pysyy toiminnassa pysyvästi jotta nykyiset integraatiot eivät lakkaa toimimasta. V1 dokumentaatio löytyy täältä.
Sähkön hinnan kallistuessa pörssisähköstä saa isoimman hyödyn siirtämällä sähkön kulutusta mahdollisimman paljon halvoille varteille. Parhaiten se onnistuu automaation avulla. Optimaalinen automaatio hakee sähkön tulevan hinnan ja sen avulla päättää milloin on paras hetki käynnistää ja sammuttaa sähkölaite.

Porssisahko.net tarjoaa yksinkertaisen hinta APIn Suomen pörssisähkön varttihinnoille. Alla olevat kaksi API endpointtia ovat vapaasti käytettävissä. Autentikaatiota ei tarvita.

§ Hae yksittäisen ajanhetken hintatieto
GET

https://api.porssisahko.net/v2/price.json?date=[iso-date-string]
Palauttaa yksittäisen ajanhetken hintatiedon. Yksikkö on snt / kWh sisältäen kyseisenä päivänä vallinneen arvonlisäveron. Kello kahden jälkeen endpoint osaa palauttaa hinnat huomisen varttihinnoille olettaen että Nord Poolin hintojen julkistuksessa ei ole ollut viivettä.
Curl esimerkki:
curl -X GET "https://api.porssisahko.net/v2/price.json?date=2025-09-19T22:26:13.634Z"

Päivämäärä parametri tulee olla ISO 8601 UTC formaatissa. Eli päättyä Z. Tämä siksi että kesäajan alkaessa ja päättyessä ei tapahdu erikoistapausta kuten paikallisessa ajassa tapahtuu.
Pyöristys tapahtuu siten että jos antamasi aika on esimerkiksi välillä 2025-09-19T22:00:00.000Z - 2025-09-19T22:14:59.999Z, palautetaan ensimmäisen vartin hinta tuolle tunnille.
Pyydettäessä hintaa ennen 1. lokakuuta 2025, palautetaan tarkasti ottaen tuntihinta mutta tällä ei ole merkitystä API vastauksesssa.
Parametrit
Nimi	Tyyppi	Selitys
date	vaadittu	Päivämäärä ISO 8601 muodossa, UTC aikavyöhykkeellä. Esimerkiksi 2025-09-19T22:26:13.634Z. Aikaisin sallittu päivämäärä on tiedonkeruun alkuhetki 2020-12-31T23:00:00.000Z.
Vastaus
200
Hinnan haku onnistui
400
Virheellinen parametri. Hinnan haku epäonnistui
404
Hintatietoa ei löydy. Pyydetty tunti on liikaa menneisyydessä tai tulevaisuudessa. Hinnan haku epäonnistui
{
  "price": 1.58
}
Node.js esimerkki
const PRICE_ENDPOINT = 'https://api.porssisahko.net/v2/price.json';

const nowUtcZ = new Date().toISOString();
const response = await fetch(`${PRICE_ENDPOINT}?date=${nowUtcZ}`);
const { price } = await response.json();

console.log(`Hinta nyt on ${price}`);
§ Hae uusimmat tiedossa olevat hinnat
GET

https://api.porssisahko.net/v2/latest-prices.json
Palauttaa uusimmat 48 tunnin hintatiedot, eli 192 erillistä hintatietoa. Kello 14 lähtien sisältää seuraavan päivän hintatiedot, olettaen että Nord Poolin hintojen julkistuksessa ei ole ollut viivettä. Ennen kello kahta sisältää hintatiedot kuluvan päivän loppuun (Norjan aikaa, klo 01:00 asti Suomen aikaa). Yksikkö on snt / kWh sisältäen kyseisenä päivänä vallinneen arvonlisäveron.

Tämä on suositeltu endpoint kun tarvitset hintatiedon joka ajanhetkenä. Kaksi API requestia päivässä, 12 tunnin välein alla olevan esimerkin mukaisesti riittää siihen että nykyinen sähkönhinta on aina tiedossa lokaalisti.

Huomio! startDate ja endDate timestampit ovat UTC aikavyöhykkeessä (Z kirjain lopussa)

Parametrit
Ei parametrejä.
Vastaus
200
Hintojen haku onnistui
{
  "prices": [
    {
      "price": 0.513,
      "startDate": "2025-09-19T22:00:00.000Z",
      "endDate": "2025-09-19T22:14:59.999Z"
    }
    {
      "price": 0.513,
      "startDate": "2025-09-19T22:15:00.000Z",
      "endDate": "2025-09-19T22:29:59.999Z"
    },
    ...,
    {
      "price": -0.002,
      "startDate": "2025-09-21T21:45:00.000Z",
      "endDate": "2025-09-21T21:59:59.999Z"
    }
  ]
}
Node.js esimerkki
const LATEST_PRICES_ENDPOINT = 'https://api.porssisahko.net/v2/latest-prices.json';

async function fetchLatestPriceData() {
  const response = await fetch(LATEST_PRICES_ENDPOINT);

  return response.json();
}

function getPriceForDate(date, prices) {
  const matchingPriceEntry = prices.find(
    (price) => new Date(price.startDate) <= date && new Date(price.endDate) > date
  );

  if (!matchingPriceEntry) {
    throw 'Price for the requested date is missing';
  }

  return matchingPriceEntry.price;
}

// Note that it's enough to call fetchLatestPriceData() once in 12 hours
const { prices } = await fetchLatestPriceData();

try {
  const now = new Date();
  const price = getPriceForDate(now, prices);

  console.log(`Hinta nyt (${now.toISOString()}): ${price} snt / kWh (sis. alv)`);
} catch (e) {
  console.error(`Hinnan haku epäonnistui, syy: ${e}`);
}