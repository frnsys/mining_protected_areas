import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = 'pk.eyJ1IjoiZnJuc3lzIiwiYSI6ImNpeGNwYjFkNDAwYXAyeWxmcm0ycmpyMXYifQ.NeU0Zkf83cbL4Tw_9Ahgww';

mapboxgl.accessToken = MAPBOX_TOKEN;
const map = new mapboxgl.Map({
  container: 'main',
  style: 'mapbox://styles/mapbox/dark-v10',
  zoom: 2,
  center: [-73.935242, 40.730610],
});

map.on('load', function () {
  map.addLayer({
    'id': 'concessions',
    'type': 'fill',
    'source': {
      type: 'vector',
      url: 'mapbox://frnsys.969ws66w'
    },
    'source-layer': 'concessions',
    'paint': {
      'fill-color': 'rgba(216,69,56,0.8)',
      'fill-outline-color': '#7a1007'
    }
  });

  map.addLayer({
    'id': 'protected',
    'type': 'fill',
    'source': {
      type: 'vector',
      url: 'mapbox://frnsys.969ws66w'
    },
    'source-layer': 'protected',
    'paint': {
      'fill-color': 'rgba(32,193,86,0.8)',
      'fill-outline-color': '#076827'
    }
  });
});

map.on('click', function(e) {
  let features = map.queryRenderedFeatures(e.point);
  features = features.reduce((acc, f) => {
    if (['protected', 'concessions'].includes(f.source)) {
      acc[f.source] = f;
    }
    return acc;
  }, {});
  if (Object.keys(features).length > 0) {
    let html = '';
    if (features['protected']) {
      let f = features['protected'].properties;
      html += `<h5 class="protected">Protected Area</h5>
        <p>
          ${f.NAME}</br>
          ${f.DESIG_ENG}
        </p>`;
    }
    if (features['concessions']) {
      let f = features['concessions'].properties;
      html += `<h5 class="concession">Mining Concession</h5>
        <p>
          Type: ${f.type || 'Not specified'}<br />
          Mineral: ${f.mineral || 'Not specified'}<br />
          Company: ${f.company || 'Not specified'}
        </p>`;
    }
    new mapboxgl.Popup()
      .setLngLat(e.lngLat)
      .setHTML(html)
      .addTo(map);
  }
});