package com.example.amazonwishlist.ui

import android.content.Intent
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.amazonwishlist.data.WishlistApi
import com.example.amazonwishlist.data.WishlistItem
import kotlinx.coroutines.launch
import java.text.NumberFormat
import java.util.*

enum class SortOrder {
    ALPHABETICAL, PRICE_LOW_HIGH, SAVINGS_HIGH_LOW
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WishlistScreen(onItemClick: (String) -> Unit, onSettingsClick: () -> Unit) {
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<WishlistItem>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var isRefreshing by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var sortOrder by remember { mutableStateOf(SortOrder.ALPHABETICAL) }
    val uriHandler = LocalUriHandler.current
    val haptic = LocalHapticFeedback.current

    fun loadItems(refresh: Boolean = false) {
        scope.launch {
            if (refresh) isRefreshing = true else isLoading = true
            try {
                items = WishlistApi.retrofitService.getItems()
                errorMessage = null
            } catch (e: Exception) {
                errorMessage = e.message
            } finally {
                isLoading = false
                isRefreshing = false
            }
        }
    }

    LaunchedEffect(Unit) {
        loadItems()
    }

    val sortedItems = remember(items, sortOrder) {
        when (sortOrder) {
            SortOrder.ALPHABETICAL -> items.sortedBy { it.title }
            SortOrder.PRICE_LOW_HIGH -> items.sortedBy { it.price ?: Double.MAX_VALUE }
            SortOrder.SAVINGS_HIGH_LOW -> items.sortedByDescending { it.savings }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("PricePulse", fontWeight = FontWeight.Black) },
                actions = {
                    IconButton(onClick = { loadItems(refresh = true) }) {
                        if (isRefreshing) {
                            CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                        }
                    }
                    var showSortMenu by remember { mutableStateOf(false) }
                    Box {
                        IconButton(onClick = { showSortMenu = true }) {
                            Icon(Icons.Default.Sort, contentDescription = "Sort")
                        }
                        DropdownMenu(expanded = showSortMenu, onDismissRequest = { showSortMenu = false }) {
                            DropdownMenuItem(
                                text = { Text("Alphabetical") },
                                onClick = { sortOrder = SortOrder.ALPHABETICAL; showSortMenu = false },
                                leadingIcon = { if (sortOrder == SortOrder.ALPHABETICAL) Icon(Icons.Default.Check, null) }
                            )
                            DropdownMenuItem(
                                text = { Text("Price: Low to High") },
                                onClick = { sortOrder = SortOrder.PRICE_LOW_HIGH; showSortMenu = false },
                                leadingIcon = { if (sortOrder == SortOrder.PRICE_LOW_HIGH) Icon(Icons.Default.Check, null) }
                            )
                            DropdownMenuItem(
                                text = { Text("Savings: High to Low") },
                                onClick = { sortOrder = SortOrder.SAVINGS_HIGH_LOW; showSortMenu = false },
                                leadingIcon = { if (sortOrder == SortOrder.SAVINGS_HIGH_LOW) Icon(Icons.Default.Check, null) }
                            )
                        }
                    }
                    IconButton(onClick = onSettingsClick) {
                        Icon(Icons.Default.Settings, contentDescription = "Manage Wishlists")
                    }
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            if (isLoading) {
                LoadingShimmer()
            } else if (errorMessage != null && items.isEmpty()) {
                EmptyState(message = "Error: $errorMessage", icon = Icons.Default.Error, onRetry = { loadItems() })
            } else if (items.isEmpty()) {
                EmptyState(message = "No items in your wishlist yet.", icon = Icons.Default.ShoppingBag, onRetry = { loadItems() })
            } else {
                val groupedItems = sortedItems.groupBy { it.wishlistName ?: "Default" }
                val expandedStates = remember { mutableStateMapOf<String, Boolean>() }
                
                groupedItems.keys.forEach { name ->
                    if (name !in expandedStates) expandedStates[name] = true
                }

                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 16.dp)
                ) {
                    groupedItems.forEach { (wishlistName, wishlistItems) ->
                        val isExpanded = expandedStates[wishlistName] ?: true
                        val wishlistUrl = wishlistItems.firstOrNull()?.wishlistUrl

                        item {
                            WishlistHeader(
                                name = wishlistName,
                                count = wishlistItems.size,
                                isExpanded = isExpanded,
                                onToggle = { 
                                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                    expandedStates[wishlistName] = !isExpanded 
                                },
                                onTitleClick = {
                                    wishlistUrl?.let { uriHandler.openUri(it) }
                                }
                            )
                        }

                        if (isExpanded) {
                            items(wishlistItems, key = { it.id }) { item ->
                                AnimatedVisibility(
                                    visible = true,
                                    enter = fadeIn() + expandVertically(),
                                    exit = fadeOut() + shrinkVertically()
                                ) {
                                    WishlistItemCard(
                                        item = item,
                                        onCardClick = { 
                                            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                                            onItemClick(item.id) 
                                        },
                                        onImageClick = { uriHandler.openUri(item.url) }
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun LoadingShimmer() {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        repeat(5) {
            Card(
                modifier = Modifier.fillMaxWidth().height(100.dp).padding(vertical = 8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
            ) {}
        }
    }
}

@Composable
fun EmptyState(message: String, icon: androidx.compose.ui.graphics.vector.ImageVector, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(icon, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.secondary)
        Spacer(modifier = Modifier.height(16.dp))
        Text(message, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyLarge)
        Spacer(modifier = Modifier.height(24.dp))
        Button(onClick = onRetry) {
            Text("Retry")
        }
    }
}

@Composable
fun WishlistHeader(
    name: String,
    count: Int,
    isExpanded: Boolean,
    onToggle: () -> Unit,
    onTitleClick: () -> Unit
) {
    Surface(
        color = MaterialTheme.colorScheme.secondaryContainer,
        modifier = Modifier.fillMaxWidth().clickable(onClick = onToggle)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSecondaryContainer
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
                Text(
                    text = "$count items",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.7f)
                )
            }
            IconButton(onClick = onTitleClick) {
                Icon(
                    imageVector = Icons.Default.OpenInNew,
                    contentDescription = "Open in Amazon",
                    tint = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

@Composable
fun WishlistItemCard(
    item: WishlistItem,
    onCardClick: () -> Unit,
    onImageClick: () -> Unit
) {
    val currencyFormatter = remember { NumberFormat.getCurrencyInstance(Locale("es", "ES")) }
    val context = LocalContext.current
    
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp),
        onClick = onCardClick,
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column {
            Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                AsyncImage(
                    model = item.imageURL,
                    contentDescription = null,
                    modifier = Modifier
                        .size(90.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color.White)
                        .clickable { onImageClick() }
                        .padding(4.dp),
                    contentScale = ContentScale.Fit
                )
                Spacer(modifier = Modifier.width(16.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = item.title,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 2,
                        fontWeight = FontWeight.Bold,
                        lineHeight = MaterialTheme.typography.titleSmall.lineHeight
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (item.priceUsed != null) {
                            Text(
                                text = currencyFormatter.format(item.priceUsed),
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.ExtraBold
                            )
                            if (item.price != null && item.price > item.priceUsed) {
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = currencyFormatter.format(item.price),
                                    style = MaterialTheme.typography.bodySmall,
                                    textDecoration = TextDecoration.LineThrough,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                                )
                            }
                        } else if (item.price != null) {
                            Text(
                                text = currencyFormatter.format(item.price),
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        } else {
                            Text("Price N/A", style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                    
                    if (item.savings > 0) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Surface(
                            color = Color(0xFFE8F5E9),
                            contentColor = Color(0xFF2E7D32),
                            shape = RoundedCornerShape(4.dp)
                        ) {
                            Text(
                                text = "-${"%.0f".format(item.savings)}%",
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f)
                )
            }
            
            HorizontalDivider(modifier = Modifier.padding(horizontal = 12.dp), thickness = 0.5.dp, color = MaterialTheme.colorScheme.outlineVariant)
            
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 4.dp),
                horizontalArrangement = Arrangement.End
            ) {
                IconButton(onClick = {
                    val sendIntent: Intent = Intent().apply {
                        action = Intent.ACTION_SEND
                        putExtra(Intent.EXTRA_TEXT, "Check out this deal on PricePulse: ${item.title}\n${item.url}")
                        type = "text/plain"
                    }
                    val shareIntent = Intent.createChooser(sendIntent, null)
                    context.startActivity(shareIntent)
                }) {
                    Icon(Icons.Default.Share, contentDescription = "Share", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                }
                IconButton(onClick = onImageClick) {
                    Icon(Icons.Default.ShoppingCart, contentDescription = "Buy Now", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                }
            }
        }
    }
}
