package com.bencao.zhiguan;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SettingsActivity extends AppCompatActivity {

    public static final String PREFS_NAME = "BencaoZhiguanPrefs";
    public static final String KEY_SERVER_URL = "server_url";
    public static final String KEY_URL_HISTORY = "url_history";
    public static final String DEMO_SERVER_URL = "https://bencao-demo.example.com";

    private EditText serverUrlInput;
    private Button saveBtn;
    private Button testBtn;
    private Button btnScan;
    private Button btnDemo;
    private TextView connectionStatus;
    private LinearLayout historyLayout;
    private TextView historyTitle;

    private ExecutorService executorService;
    private Handler mainHandler;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        initViews();
        executorService = Executors.newSingleThreadExecutor();
        mainHandler = new Handler(Looper.getMainLooper());

        loadSavedUrl();
        loadUrlHistory();
        setupClickListeners();
    }

    private void initViews() {
        serverUrlInput = findViewById(R.id.serverUrlInput);
        saveBtn = findViewById(R.id.saveBtn);
        testBtn = findViewById(R.id.testBtn);
        btnScan = findViewById(R.id.btnScan);
        btnDemo = findViewById(R.id.btnDemo);
        connectionStatus = findViewById(R.id.connectionStatus);
        historyLayout = findViewById(R.id.historyLayout);
        historyTitle = findViewById(R.id.historyTitle);
    }

    private void loadSavedUrl() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String savedUrl = prefs.getString(KEY_SERVER_URL, "");
        if (!TextUtils.isEmpty(savedUrl)) {
            serverUrlInput.setText(savedUrl);
            serverUrlInput.setSelection(savedUrl.length());
        }
    }

    private void loadUrlHistory() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        Set<String> historySet = prefs.getStringSet(KEY_URL_HISTORY, new HashSet<>());
        List<String> history = new ArrayList<>(historySet);

        if (history.isEmpty()) {
            historyTitle.setVisibility(View.GONE);
            historyLayout.setVisibility(View.GONE);
            return;
        }

        historyTitle.setVisibility(View.VISIBLE);
        historyLayout.setVisibility(View.VISIBLE);
        historyLayout.removeAllViews();

        for (final String url : history) {
            TextView historyItem = new TextView(this);
            historyItem.setText(url);
            historyItem.setTextSize(13);
            historyItem.setTextColor(getResources().getColor(R.color.text_secondary));
            historyItem.setPadding(24, 16, 24, 16);
            historyItem.setBackgroundResource(R.drawable.edittext_background);
            historyItem.setOnClickListener(v -> {
                serverUrlInput.setText(url);
                serverUrlInput.setSelection(url.length());
            });

            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT);
            params.setMargins(0, 0, 0, 12);
            historyItem.setLayoutParams(params);

            historyLayout.addView(historyItem);
        }
    }

    private void setupClickListeners() {
        saveBtn.setOnClickListener(v -> saveAndContinue());
        testBtn.setOnClickListener(v -> testConnection());

        // 扫码连接
        btnScan.setOnClickListener(v -> {
            // 尝试调用系统扫码应用
            try {
                Intent intent = new Intent("com.google.zxing.client.android.SCAN");
                intent.putExtra("SCAN_MODE", "QR_CODE_MODE");
                startActivityForResult(intent, 0);
            } catch (Exception e) {
                // 如果没有扫码应用，提示用户手动输入
                new androidx.appcompat.app.AlertDialog.Builder(this)
                        .setTitle("扫码连接")
                        .setMessage("请在电脑端登录系统后，打开「APP连接」页面，显示二维码。\n\n您的手机未安装扫码应用，可以：\n1. 安装微信/支付宝扫码\n2. 或手动输入服务器地址")
                        .setPositiveButton("手动输入", (dialog, which) -> {
                            serverUrlInput.requestFocus();
                        })
                        .setNegativeButton("取消", null)
                        .show();
            }
        });

        // 使用演示服务器
        btnDemo.setOnClickListener(v -> {
            serverUrlInput.setText(DEMO_SERVER_URL);
            serverUrlInput.setSelection(DEMO_SERVER_URL.length());
            Toast.makeText(this, "已填入演示服务器地址", Toast.LENGTH_SHORT).show();
        });

        // 快捷按钮
        Button btnEmulator = findViewById(R.id.btnEmulator);
        Button btnLocal = findViewById(R.id.btnLocal);
        Button btnLan = findViewById(R.id.btnLan);

        btnEmulator.setOnClickListener(v -> {
            serverUrlInput.setText("http://10.0.2.2:5000");
            serverUrlInput.setSelection(serverUrlInput.getText().length());
        });

        btnLocal.setOnClickListener(v -> {
            serverUrlInput.setText("http://127.0.0.1:5000");
            serverUrlInput.setSelection(serverUrlInput.getText().length());
        });

        btnLan.setOnClickListener(v -> {
            serverUrlInput.setText("http://192.168.");
            serverUrlInput.setSelection(serverUrlInput.getText().length());
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 0 && resultCode == RESULT_OK) {
            String contents = data.getStringExtra("SCAN_RESULT");
            if (contents != null && !contents.isEmpty()) {
                serverUrlInput.setText(contents);
                serverUrlInput.setSelection(contents.length());
                Toast.makeText(this, "扫码成功，已填入服务器地址", Toast.LENGTH_SHORT).show();
                // 自动保存并进入
                saveAndContinue();
            }
        }
    }

    private void saveAndContinue() {
        String url = serverUrlInput.getText().toString().trim();

        if (TextUtils.isEmpty(url)) {
            showConnectionStatus("请输入服务器地址", false);
            return;
        }

        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
            serverUrlInput.setText(url);
        }

        // 去除末尾的斜杠
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }

        // 保存到SharedPreferences
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();
        editor.putString(KEY_SERVER_URL, url);

        // 保存到历史记录
        Set<String> historySet = prefs.getStringSet(KEY_URL_HISTORY, new HashSet<>());
        Set<String> newHistorySet = new HashSet<>(historySet);
        newHistorySet.add(url);
        // 最多保存5条历史记录
        if (newHistorySet.size() > 5) {
            List<String> historyList = new ArrayList<>(newHistorySet);
            newHistorySet = new HashSet<>(historyList.subList(0, 5));
        }
        editor.putStringSet(KEY_URL_HISTORY, newHistorySet);
        editor.apply();

        Toast.makeText(this, "服务器地址已保存", Toast.LENGTH_SHORT).show();

        // 跳转到MainActivity
        Intent intent = new Intent(this, MainActivity.class);
        intent.putExtra("server_url", url);
        startActivity(intent);
        finish();
    }

    private void testConnection() {
        String url = serverUrlInput.getText().toString().trim();

        if (TextUtils.isEmpty(url)) {
            showConnectionStatus("请输入服务器地址", false);
            return;
        }

        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }

        final String finalUrl = url;
        showConnectionStatus("正在测试连接...", true);

        testBtn.setEnabled(false);
        saveBtn.setEnabled(false);

        executorService.execute(() -> {
            boolean success = false;
            String message = "";

            try {
                URL testUrl = new URL(finalUrl + "/index.html");
                HttpURLConnection connection = (HttpURLConnection) testUrl.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);
                connection.connect();

                int responseCode = connection.getResponseCode();
                if (responseCode == 200) {
                    success = true;
                    message = "连接成功！服务器响应正常";
                } else {
                    message = "服务器响应异常，状态码：" + responseCode;
                }
                connection.disconnect();
            } catch (IOException e) {
                message = "连接失败：" + e.getMessage();
            } catch (Exception e) {
                message = "测试出错：" + e.getMessage();
            }

            final boolean finalSuccess = success;
            final String finalMessage = message;

            mainHandler.post(() -> {
                showConnectionStatus(finalMessage, finalSuccess);
                testBtn.setEnabled(true);
                saveBtn.setEnabled(true);
            });
        });
    }

    private void showConnectionStatus(String message, boolean isTesting) {
        connectionStatus.setVisibility(View.VISIBLE);
        connectionStatus.setText(message);

        if (isTesting) {
            connectionStatus.setTextColor(getResources().getColor(R.color.text_secondary));
        } else if (message.contains("成功")) {
            connectionStatus.setTextColor(getResources().getColor(R.color.success));
        } else {
            connectionStatus.setTextColor(getResources().getColor(R.color.error));
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (executorService != null && !executorService.isShutdown()) {
            executorService.shutdown();
        }
    }
}
