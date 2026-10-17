package com.candywriter.bitlife.ui.adapters;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.candywriter.bitlife.R;
import com.candywriter.bitlife.models.CharacterState;

import java.util.ArrayList;
import java.util.List;

public class LifeLogAdapter extends RecyclerView.Adapter<LifeLogAdapter.LogViewHolder> {

    private List<CharacterState.LifeYearLog> yearLogs = new ArrayList<>();

    public void submitList(List<CharacterState.LifeYearLog> logs) {
        this.yearLogs = logs != null ? new ArrayList<>(logs) : new ArrayList<>();
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public LogViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_life_log, parent, false);
        return new LogViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull LogViewHolder holder, int position) {
        CharacterState.LifeYearLog yearLog = yearLogs.get(position);
        holder.tvAgeHeader.setText("العمر: " + yearLog.age + " سنة");

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < yearLog.events.size(); i++) {
            if (i > 0) sb.append("\n\n");
            sb.append("• ").append(yearLog.events.get(i));
        }
        holder.tvAgeEvents.setText(sb.toString());
    }

    @Override
    public int getItemCount() {
        return yearLogs.size();
    }

    static class LogViewHolder extends RecyclerView.ViewHolder {
        final TextView tvAgeHeader;
        final TextView tvAgeEvents;

        LogViewHolder(@NonNull View itemView) {
            super(itemView);
            tvAgeHeader = itemView.findViewById(R.id.tvAgeHeader);
            tvAgeEvents = itemView.findViewById(R.id.tvAgeEvents);
        }
    }
}
