package com.project.weatherdatafetcher.dto;

import java.util.List;

public class MappedObject {
    private String date_from;
    private String date_to;
    private List<ApiResponse> days;

    public MappedObject(){

    }

    public List<ApiResponse> getDays() {
        return days;
    }

    public String getDate_from() {
        return date_from;
    }

    public String getDate_to() {
        return date_to;
    }

    public void setDate_from(String date_from) {
        this.date_from = date_from;
    }

    public void setDate_to(String date_to) {
        this.date_to = date_to;
    }

    public void setDays(List<ApiResponse> days) {
        this.days = days;
    }

    private MappedObject(MappedObjectBuilder builder) {
        this.date_from = builder.date_from;
        this.date_to = builder.date_to;
        this.days = builder.days;
    }


    public static MappedObjectBuilder builder() {
        return new MappedObjectBuilder();
    }

    public static class MappedObjectBuilder {
        private String date_from;
        private String date_to;
        private List<ApiResponse> days;

        public MappedObjectBuilder date_from(String date_from) {
            this.date_from = date_from;
            return this;
        }

        public MappedObjectBuilder date_to(String date_to) {
            this.date_to = date_to;
            return this;
        }

        public MappedObjectBuilder days(List<ApiResponse> days) {
            this.days = days;
            return this;
        }

        public MappedObject build() {
            return new MappedObject(this);
        }
    }
}
