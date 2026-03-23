package com.example.amazonwishlist.ui

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
    var showSortMenu by remember { mutableStateOf(false) }
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
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                    actionIconContentColor = MaterialTheme.colorScheme.onSurface
                ),
                actions = {
                    IconButton(onClick = { loadItems(refresh = true) }) {
                        if (isRefreshing) {
                            CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                        }
                    }
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
        repeat(8) {
            Card(
                modifier = Modifier.fillMaxWidth().height(70.dp).padding(vertical = 4.dp),
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
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSecondaryContainer,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = name,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
                Text(
                    text = "$count items",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.7f)
                )
            }
            IconButton(onClick = onTitleClick, modifier = Modifier.size(32.dp)) {
                Icon(
                    imageVector = Icons.Default.OpenInNew,
                    contentDescription = "Open in Amazon",
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(18.dp)
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
    
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
        onClick = onCardClick,
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(modifier = Modifier.padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
            AsyncImage(
                model = item.imageURL,
                contentDescription = null,
                modifier = Modifier
                    .size(60.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(Color.White)
                    .clickable { onImageClick() }
                    .padding(2.dp),
                contentScale = ContentScale.Fit
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = item.title,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    fontWeight = FontWeight.Bold,
                    lineHeight = MaterialTheme.typography.titleSmall.lineHeight
                )
                
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "New: ${item.price?.let { currencyFormatter.format(it) } ?: "N/A"}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    
                    Spacer(modifier = Modifier.width(8.dp))
                    
                    Text(
                        text = "Used: ${item.priceUsed?.let { currencyFormatter.format(it) } ?: "N/A"}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold
                    )

                    if (item.savings > 0) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "-${"%.0f".format(item.savings)}%",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF2E7D32)
                        )
                    }
                }
            }
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.3f),
                modifier = Modifier.size(20.dp)
            )
        }
    }
}
