package com.example.amazonwishlist.ui

import android.content.Intent
import android.graphics.Color
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import coil.compose.AsyncImage
import com.example.amazonwishlist.data.PriceHistory
import com.example.amazonwishlist.data.WishlistApi
import com.example.amazonwishlist.data.WishlistItem
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter
import kotlinx.coroutines.launch
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ItemDetailScreen(itemId: String, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    var item by remember { mutableStateOf<WishlistItem?>(null) }
    var history by remember { mutableStateOf<List<PriceHistory>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val currencyFormatter = remember { NumberFormat.getCurrencyInstance(Locale("es", "ES")) }

    LaunchedEffect(itemId) {
        scope.launch {
            try {
                // Fetch all items and find the specific one
                val allItems = WishlistApi.retrofitService.getItems()
                item = allItems.find { it.id == itemId }
                
                // Fetch history
                history = WishlistApi.retrofitService.getItemHistory(itemId)
                isLoading = false
            } catch (e: Exception) {
                errorMessage = e.message
                isLoading = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Item Details") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).padding(16.dp)) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.fillMaxSize().wrapContentSize())
            } else if (errorMessage != null) {
                Text(text = "Error: $errorMessage", color = MaterialTheme.colorScheme.error)
            } else if (item != null) {
                Row(modifier = Modifier.fillMaxWidth()) {
                    AsyncImage(
                        model = item!!.imageURL,
                        contentDescription = null,
                        modifier = Modifier
                            .size(120.dp)
                            .padding(8.dp),
                        contentScale = ContentScale.Fit
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(text = item!!.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "New Price: ${item!!.price?.let { currencyFormatter.format(it) } ?: "N/A"}",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text(
                            text = "Used Price: ${item!!.priceUsed?.let { currencyFormatter.format(it) } ?: "N/A"}",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
                
                Spacer(modifier = Modifier.height(24.dp))
                
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    val context = LocalContext.current
                    val uriHandler = LocalUriHandler.current
                    
                    Button(onClick = { uriHandler.openUri(item!!.url) }, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Default.ShoppingCart, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Buy Now")
                    }
                    
                    Spacer(modifier = Modifier.width(16.dp))
                    
                    OutlinedButton(onClick = {
                        val sendIntent: Intent = Intent().apply {
                            action = Intent.ACTION_SEND
                            putExtra(Intent.EXTRA_TEXT, "Check out this deal on PricePulse: ${item!!.title}\n${item!!.url}")
                            type = "text/plain"
                        }
                        val shareIntent = Intent.createChooser(sendIntent, null)
                        context.startActivity(shareIntent)
                    }, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Default.Share, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Share")
                    }
                }
                
                Spacer(modifier = Modifier.height(32.dp))
                Text(text = "Price History", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(16.dp))
                
                PriceHistoryGraph(history)
            }
        }
    }
}

@Composable
fun PriceHistoryGraph(history: List<PriceHistory>) {
    if (history.isEmpty()) {
        Text("No history available")
        return
    }

    AndroidView(
        modifier = Modifier
            .fillMaxWidth()
            .height(300.dp),
        factory = { context ->
            LineChart(context).apply {
                description.isEnabled = false
                setTouchEnabled(true)
                setPinchZoom(true)
                
                xAxis.position = XAxis.XAxisPosition.BOTTOM
                xAxis.setDrawGridLines(false)
                xAxis.granularity = 1f
                
                axisLeft.setDrawGridLines(true)
                axisRight.isEnabled = false
            }
        },
        update = { chart ->
            val newPriceEntries = mutableListOf<Entry>()
            val usedPriceEntries = mutableListOf<Entry>()
            val dates = mutableListOf<String>()

            val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
            val outputFormat = SimpleDateFormat("dd/MM", Locale.getDefault())

            history.forEachIndexed { index, record ->
                if (record.price != null) {
                    newPriceEntries.add(Entry(index.toFloat(), record.price.toFloat()))
                }
                if (record.priceUsed != null) {
                    usedPriceEntries.add(Entry(index.toFloat(), record.priceUsed.toFloat()))
                }
                
                try {
                    val date = inputFormat.parse(record.timestamp)
                    dates.add(if (date != null) outputFormat.format(date) else "")
                } catch (e: Exception) {
                    dates.add("")
                }
            }

            val newPriceDataSet = LineDataSet(newPriceEntries, "New Price").apply {
                color = Color.RED
                setCircleColor(Color.RED)
                lineWidth = 2f
                circleRadius = 3f
                setDrawValues(false)
            }

            val usedPriceDataSet = LineDataSet(usedPriceEntries, "Used Price").apply {
                color = Color.GREEN
                setCircleColor(Color.GREEN)
                lineWidth = 2f
                circleRadius = 3f
                setDrawValues(false)
            }

            chart.data = LineData(newPriceDataSet, usedPriceDataSet)
            chart.xAxis.valueFormatter = IndexAxisValueFormatter(dates)
            chart.invalidate()
        }
    )
}
