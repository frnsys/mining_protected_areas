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
map.dragRotate.disable();
map.touchZoomRotate.disableRotation();

map.on('load', function () {
  map.addLayer({
    'id': 'protected_overlap',
    'type': 'fill',
    'source': {
      type: 'vector',
      url: 'mapbox://frnsys.969ws66w'
    },
    'source-layer': 'protected_overlap',
    'paint': {
      'fill-color': 'rgba(252,208,63,0.8)',
      'fill-outline-color': '#fcd03f'
    }
  });

  map.addLayer({
    'id': 'protected_no_overlap',
    'type': 'fill',
    'source': {
      type: 'vector',
      url: 'mapbox://frnsys.969ws66w'
    },
    'source-layer': 'protected_no_overlap',
    'paint': {
      'fill-color': 'rgba(32,193,86,0.8)',
      'fill-outline-color': '#076827'
    }
  });

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


  // Object.keys(data).forEach((id) => {
  //   let meta = data[id];
  //   map.addSource(`sat_${id}`, {
  //     'type': 'image',
  //     'url': `/assets/${id}.png`,
  //     'coordinates': meta.box
  //   });
  //   map.addLayer({
  //     'id': `sat_${id}`,
  //     'source': `sat_${id}`,
  //     'type': 'raster',
  //     'paint': {'raster-opacity': 0.85}
  //   });
  // });
});

map.on('click', function(e) {
  let features = map.queryRenderedFeatures(e.point);
  console.log(features);
  features = features.reduce((acc, f) => {
    // TODO include multiple overlapping features
    if (['protected_overlap', 'protected_no_overlap', 'concessions'].includes(f.source)) {
      acc[f.source] = f;
    }
    return acc;
  }, {});
  if (Object.keys(features).length > 0) {
    let html = '';
    if (features['protected_overlap']) {
      let f = features['protected_overlap'].properties;
      html += `<h5 class="protected">Protected Area</h5>
        <p>
          ${f.NAME}</br>
          ${f.DESIG_ENG}
        </p>`;
    }
    if (features['protected_no_overlap']) {
      let f = features['protected_no_overlap'].properties;
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