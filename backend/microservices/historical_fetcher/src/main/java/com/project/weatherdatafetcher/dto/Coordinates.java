package com.project.weatherdatafetcher.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

// Deserializes regions_api's combined GET /wmo-indexes/{wmo_index} response,
// which also carries region_id - ignored here since only coordinates/name
// are needed for the Open-Meteo Archive lookup.
@JsonIgnoreProperties(ignoreUnknown = true)
public class Coordinates {
    private String wmo_index;
    private Double lat;
    private Double lng;
    private String name;

    public Coordinates(){

    }
    public Coordinates(String wmo_index, Double lat, Double lng, String name){

        this.wmo_index = wmo_index;
        this.lat = lat;
        this.lng = lng;
        this.name = name;
    }

    public Double getLat() {
        return lat;
    }

    public Double getLng() {
        return lng;
    }

    public String getWmo_index() {
        return wmo_index;
    }

    public String getName() {
        return name;
    }

    public void setWmo_index(String wmo_index) {
        this.wmo_index = wmo_index;
    }

    public void setLat(Double lat) {
        this.lat = lat;
    }

    public void setLng(Double lng) {
        this.lng = lng;
    }

    public void setName(String name) {
        this.name = name;
    }
}
