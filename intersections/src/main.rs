extern crate pbr;
extern crate geo;
extern crate geojson;
extern crate rayon;

use std::fs;
use std::env;
use rayon::prelude::*;
use serde_json::json;
use geojson::GeoJson;
use geo::{Geometry, Polygon};
use geo::prelude::Intersects;
use std::convert::TryInto;
use pbr::ProgressBar;
use std::fs::File;
use std::io::BufReader;
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use geo::algorithm::euclidean_distance::nearest_neighbour_distance;

fn process_geojson(gj: &GeoJson) -> Vec<Geometry<f64>>{
    match *gj {
        GeoJson::FeatureCollection(ref ctn) => {
            ctn.features.iter().filter_map(|feat| {
                if let Some(ref geom) = feat.geometry {
                    Some(geom.value.clone().try_into().unwrap())
                } else {
                    None
                }
            }).collect()
        },
        _ => {
            vec![]
        }
    }
}

// Had issues with the geo Polygon-Polygon implementation of
// the EuclideanDistance trait. The `min_poly_dist` function
// wouldn't converge sometimes.
fn distance(poly: &Polygon<f64>, poly2: &Polygon<f64>) -> f64 {
    if poly.intersects(poly2) {
        return 0.;
    }
    nearest_neighbour_distance(&poly.exterior(), &poly2.exterior())
}

fn within(g: &Geometry<f64>, q: &Geometry<f64>, buffer: f64) -> bool {
    match &g {
        Geometry::Polygon(g_) => {
            match &q {
                Geometry::Polygon(q_) => {
                    distance(g_, q_) <= buffer
                },
                Geometry::MultiPolygon(q_) => {
                    q_.0.iter().any(|q__| distance(g_, q__) <= buffer)
                },
                _ => false
            }
        },
        Geometry::MultiPolygon(g_) => {
            match &q {
                Geometry::Polygon(q_) => {
                    g_.0.iter().any(|g__| distance(g__, q_) <= buffer)
                },
                Geometry::MultiPolygon(q_) => {
                    q_.0.iter().any(|q__| g_.0.iter().any(|g__| distance(g__, q__) <= buffer))
                },
                _ => false
            }
        },
        _ => false
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let buffer: f64 = args[1].parse().unwrap(); // meters
    let candidates_path = &args[2];
    let concessions_path = &args[3];
    let protected_path = &args[4];
    let out_path = &args[5];
    println!("Buffer: {:?}m", buffer);

    let file = File::open(candidates_path).expect("could not open file");
    let reader = BufReader::new(file);
    let isx: HashMap<usize, Vec<usize>> = serde_json::from_reader(reader).expect("error while reading json");

    println!("Loading concessions...");
    let concession_geoms = {
        let contents = fs::read_to_string(concessions_path)
            .expect("Something went wrong reading the file");
        let geojson = contents.parse::<GeoJson>().unwrap();
        process_geojson(&geojson)
    };
    println!("Concessions: {:?}", concession_geoms.len());

    println!("Loading protected...");
    let protected_geoms = {
        let contents = fs::read_to_string(protected_path)
            .expect("Something went wrong reading the file");
        let geojson = contents.parse::<GeoJson>().unwrap();
        process_geojson(&geojson)
    };
    println!("Protected: {:?}", protected_geoms.len());

    let pb = ProgressBar::new(concession_geoms.len() as u64);
    let pbm = Arc::new(Mutex::new(pb));
    let results: Vec<HashSet<usize>> = concession_geoms.into_par_iter().enumerate().filter_map(|(i, g)| {
        let mut overlapped = HashSet::new();
        match isx.get(&i) {
            Some(matches) => {
                for &j in matches {
                    let q = &protected_geoms[j];
                    if within(&g, q, buffer) {
                        overlapped.insert(j);
                    }
                }
            },
            None => ()
        }
        let mut pb = pbm.lock().unwrap();
        pb.inc();
        if overlapped.len() > 0 {
            Some(overlapped)
        } else {
            None
        }
    }).collect();

    let mut overlapped = HashSet::new();
    for overlaps in &results {
        for j in overlaps {
            overlapped.insert(j);
        }
    }

    let json = json!(results);
    serde_json::to_writer(&File::create(out_path).unwrap(), &json).unwrap();
    println!("{:?} ({:?}) protected areas w/in {:?}m",
        overlapped.len() as f64/protected_geoms.len() as f64, overlapped.len(), buffer);
}
