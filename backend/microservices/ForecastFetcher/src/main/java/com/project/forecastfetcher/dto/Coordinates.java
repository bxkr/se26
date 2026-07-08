package com.project.forecastfetcher.dto;

public class Coordinates {
    private String wmo_index;
    private Double lat;
    private Double lng;

    public Coordinates(){

    }
    public Coordinates(String wmo_index, Double lat, Double lng){

        this.wmo_index = wmo_index;
        this.lat = lat;
        this.lng = lng;
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

    public void setWmo_index(String wmo_index) {
        this.wmo_index = wmo_index;
    }

    public void setLat(Double lat) {
        this.lat = lat;
    }

    public void setLng(Double lng) {
        this.lng = lng;
    }
}
