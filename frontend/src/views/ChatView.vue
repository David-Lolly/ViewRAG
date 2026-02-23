<template>
  <div class="flex w-full h-full bg-background-main relative"
       @drop.prevent="handleDrop"
       @dragover.prevent="handleDragOver"
       @dragleave.prevent="handleDragLeave"
       @dragenter.prevent="handleDragEnter">
    
    <!-- 全局拖拽提示层 -->
    <div 
      v-if="isDragging" 
      class="fixed inset-0 bg-background-secondary bg-opacity-95 backdrop-blur-sm z-[10000] flex items-center justify-center pointer-events-none"
    >
      <div class="bg-white rounded-3xl shadow-2xl px-12 py-10 border-4 border-dashed border-button-active max-w-md">
        <div class="text-center">
          <div class="mb-6">
            <svg class="w-20 h-20 mx-auto text-button-active" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
          </div>
          <h3 class="text-2xl font-bold text-text-primary mb-3">释放以上传文件</h3>
          <p class="text-base text-text-secondary mb-2">
            支持文档：PDF、Word、Excel、PPT、TXT
          </p>
          <p class="text-base text-text-secondary">
            支持图片：PNG、JPG、GIF、WebP
          </p>
          <p class="text-sm text-gray-500 mt-4">
            图片上传需要选择多模态模型
          </p>
        </div>
      </div>
    </div>
    
    <ChatSidebar
      :sessions="sessions"
      :current-session-id="currentSessionId"
      :user-id="userId"
      :is-open="isSidebarOpen"
      @toggle="toggleSidebar"
      @new-chat="createNewSession"
      @session-select="selectSession"
      @logout="handleLogout" 
      @edit-config="navigateToConfig"
      @go-to-kb="navigateToKnowledgeBase" />

    <main class="relative flex-1 flex flex-col transition-all duration-300 ease-in-out"
          :style="{
            marginLeft: isSidebarOpen ? '288px' : '0px'
          }">

      <!-- 右上角文件管理按钮 -->
      <button
        v-if="allSessionDocuments.length > 0"
        @click="showFilePanel = !showFilePanel"
        class="absolute top-4 right-4 z-40 w-9 h-9 flex items-center justify-center rounded-lg bg-white border border-gray-200 shadow-sm hover:bg-gray-50 hover:border-gray-300 transition-all duration-200"
        title="查看会话文件"
      >
        <!-- 盒子/档案图标 -->
        <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
        </svg>
        <!-- 数量角标 -->
        <span class="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-blue-500 text-white text-[10px] font-bold px-1">
          {{ allSessionDocuments.length }}
        </span>
      </button>

      <!-- 文件管理面板 -->
      <SessionFilePanel
        :visible="showFilePanel"
        :documents="allSessionDocuments"
        @close="showFilePanel = false"
      />

      <!-- 文档处理失败错误卡片（右上角） -->
      <div
        v-if="hasFailedDocuments"
        class="absolute right-4 z-50 bg-red-50 border border-red-200 rounded-lg shadow-lg px-4 py-3 max-w-sm animate-fade-in"
        :class="allSessionDocuments.length > 0 ? 'top-16' : 'top-4'"
      >
        <div class="flex items-start gap-2">
          <svg class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
          </svg>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-red-800">文档处理失败</p>
            <div v-for="doc in sessionDocuments.filter(d => d.status === 'FAILED')" :key="doc.doc_id" class="text-xs text-red-600 mt-1 truncate">
              {{ doc.file_name }}: {{ doc.error_message || '处理失败' }}
            </div>
          </div>
        </div>
      </div>

      <div 
        class="flex-1 overflow-y-auto px-6 pt-4" 
        ref="messagesContainer"
        @scroll="handleScroll"
      >
        <div v-if="!currentSessionId" class="flex items-center justify-center h-full">
          <div class="text-center max-w-md animate-fade-in">
            <img src="@/assets/ViewRAG.png" alt="ViewRAG Logo" class="w-24 h-auto mx-auto mb-6 shadow-floating object-contain">
            <h1 class="text-4xl font-bold mb-3 text-text-primary">ViewRAG</h1>
            <p class="text-text-secondary text-lg leading-relaxed">
              告别纯文本RAG，让问答图文并茂<br>
              <span class="text-sm opacity-75">输入内容，开始你的第一次对话吧！</span>
            </p>
          </div>
        </div>

        <div v-else class="max-w-4xl mx-auto" :style="{ paddingBottom: dynamicPaddingBottom }">
          <ChatMessage
            v-for="(msg, index) in messages"
            :key="msg.message_id"
            :message="msg"
            :user-id="userId"
            :is-streaming="index === messages.length - 1 && isLoading && msg.role === 'assistant' && !msg.streamEnded"
            :search-steps="index === messages.length - 1 ? currentSearchSteps : []"
            :is-marked-for-deletion="editingMessageIndex !== null && index > editingMessageIndex"
            :has-error="msg.hasError"
            :error-message="msg.errorMessage"
            :references="msg.references || []"
            :is-interactive="msg.isInteractive || false"
            :image-mapping="msg._imageMapping || new Map()"
            :references-map="msg._referencesMap || new Map()"
            :retrieved-documents="msg.retrieved_documents || []"
            :pending-scenario="index === messages.length - 1 ? pendingScenario : null"
            :mascot-status="index === messages.length - 1 && msg.role === 'assistant' ? mascotStatus : 'idle'"
            @regenerate="handleRegenerate"
            @edit="handleEdit"
            @retry="handleRetry"
            class="mb-2 animate-slide-in"
            />
        </div>
      </div>

      
      <div ref="inputAreaRef" class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background-main via-background-main to-transparent pt-3 pb-3 px-6">
        <div class="max-w-4xl mx-auto">
          <div class="bg-background-card rounded-xl shadow-input-card border border-gray-100 overflow-hidden">

            <!-- 图片预览区域（移到顶部） -->
            <div v-if="pendingImages.length > 0" class="px-4 pt-3 pb-3 border-b border-gray-100 flex flex-wrap gap-2">
              <div v-for="img in pendingImages" :key="img.id" class="relative inline-block">
                <img :src="img.previewUrl" :alt="img.file.name" 
                     class="w-24 h-24 object-cover rounded-lg border border-gray-200 shadow-sm" 
                     :class="{ 'opacity-50': img.uploading }" />
                
                <!-- 上传中遮罩层 -->
                <div v-if="img.uploading" class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-40 rounded-lg">
                  <svg class="animate-spin h-6 w-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                
                <!-- 上传成功标识 -->
                <div v-if="!img.uploading && img.url" class="absolute top-1 left-1 bg-green-500 text-white px-1 py-0.5 rounded text-xs font-medium flex items-center shadow-md">
                  <svg class="w-2 h-2 mr-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                  </svg>
                  ✓
                </div>
                
                <!-- 删除按钮 -->
                <button
                  type="button"
                  @click="removeImage(img.id)"
                  :disabled="img.uploading"
                  class="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full hover:bg-red-600 flex items-center justify-center shadow-md transition-all duration-200 hover:scale-110 text-xs"
                  :class="{ 'opacity-50 cursor-not-allowed': img.uploading }"
                  title="删除图片"
                >
                  ×
                </button>
                
                <!-- 文件名提示 -->
                <div class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-60 text-white text-xs px-1 py-0.5 rounded-b-lg truncate">
                  {{ img.file.name }}
                </div>
              </div>
              
              <!-- 添加更多图片按钮 -->
              <button
                v-if="pendingImages.length < 5"
                type="button"
                @click="triggerImageUpload"
                class="w-24 h-24 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center hover:border-blue-500 hover:bg-blue-50 transition-all duration-200"
                title="添加更多图片（最多5张）"
              >
                <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                </svg>
              </button>
            </div>

            <!-- 文档卡片预览区域（不显示失败的文档） -->
            <div v-if="pendingOrCompletedDocuments.length > 0" class="px-4 pt-3 pb-3 border-b border-gray-100 flex flex-wrap gap-2">
              <div
                v-for="doc in pendingOrCompletedDocuments"
                :key="doc.doc_id"
                class="flex items-center gap-2 px-3 py-2 rounded-lg border text-sm min-w-[180px] max-w-[260px]"
                :class="{
                  'border-gray-200 bg-gray-50': doc.status === 'UPLOADING' || doc.status === 'QUEUED',
                  'border-blue-200 bg-blue-50': ['PARSING','CHUNKING','ENRICHING','VECTORIZING'].includes(doc.status),
                  'border-green-200 bg-green-50': doc.status === 'COMPLETED',
                }"
              >
                <!-- 状态图标 -->
                <div class="flex-shrink-0">
                  <!-- 上传/处理中 旋转图标 -->
                  <svg v-if="doc.status !== 'COMPLETED'" class="w-5 h-5 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <!-- 完成 ✓ -->
                  <svg v-else class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                  </svg>
                </div>
                <!-- 文件名 + 进度 -->
                <div class="flex-1 min-w-0">
                  <div class="truncate text-text-primary text-xs font-medium">{{ doc.file_name }}</div>
                  <div class="text-xs text-text-secondary">{{ doc.status === 'COMPLETED' ? '已完成' : doc.step + ' ' + doc.progress + '%' }}</div>
                </div>
                <!-- 删除按钮（任何状态都可删除） -->
                <button
                  type="button"
                  @click="removeSessionDocument(doc.doc_id)"
                  class="flex-shrink-0 w-4 h-4 text-gray-400 hover:text-red-500 transition-colors"
                  title="移除"
                >
                  <svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
                </button>
              </div>
            </div>

            <form @submit.prevent class="relative flex flex-col">
              <div 
                class="flex-1 relative px-4 pt-3 pb-2"
              >
                <!-- 已选知识库标签 -->
                <div v-if="selectedKbId" class="flex items-center gap-1 mb-2">
                  <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700 border border-blue-200">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                    </svg>
                    @{{ selectedKbName }}
                    <button
                      type="button"
                      @click="clearSelectedKb"
                      class="ml-0.5 hover:text-blue-900 transition-colors"
                      title="取消选择知识库"
                    >
                      <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                      </svg>
                    </button>
                  </span>
                </div>

                <textarea
                  v-model="userInput"
                  @input="handleTextareaInput"
                  @keydown.enter.exact.prevent="handleEnter"
                  @paste="handlePaste"
                  ref="textareaRef"
                  :disabled="isLoading"
                  class="w-full resize-none border-none outline-none bg-transparent text-text-primary placeholder-text-secondary leading-relaxed textarea-scrollable"
                  :style="{ maxHeight: '144px', minHeight: '24px', fontSize: '1rem' }"
                  rows="1"
                  placeholder="输入你的问题..."
                ></textarea>

                <div class="h-0.5 bg-gradient-to-r from-transparent via-gray-200 to-transparent opacity-30 mt-1.5"></div>
              </div>

              <!-- 底部操作栏 -->
              <div class="flex items-center justify-between px-4 py-2.5 gap-3">
                <!-- 左侧：加号按钮和下拉菜单 -->
                <div class="button-group">
                  <div class="relative group">
                    <button
                      ref="uploadMenuButton"
                      type="button"
                      @click="toggleUploadMenu"
                      class="chat-button flex items-center justify-center w-10 h-10 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 hover:border-gray-300 text-gray-600 hover:text-gray-900 transition-all duration-300 focus:outline-none shadow-sm hover:shadow-inner active:shadow-inner"
                    >
                      <svg 
                        class="w-5 h-5 transition-transform duration-300 ease-in-out" 
                        :class="{ 'rotate-45': showMenuDropdown }"
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24" 
                        stroke-width="2.5"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"></path>
                      </svg>
                    </button>
                  </div>
                  

                </div>
                
                <!-- 右侧：模型选择器和发送按钮 -->
                <div class="button-group">
                  <!-- 模型选择器 -->
                  <div class="flex-shrink-0">
                    <ModelSelector
                      :models="availableModels"
                      :selectedModel="selectedModel"
                      @model-selected="handleModelSelect"
                    />
                  </div>
                  
                  <!-- 发送按钮 -->
                  <button
                    type="button"
                    @click="isLoading ? handleStop() : sendMessage()"
                    :disabled="!isLoading && (!userInput.trim() || hasUploadingImages || isDocumentProcessing || hasFailedDocuments)"
                    class="chat-button w-10 h-10 rounded-lg font-semibold transition-all duration-300 relative flex items-center justify-center flex-shrink-0 border focus:outline-none shadow-sm hover:shadow-inner active:shadow-inner"
                    :class="[
                      isLoading
                        ? 'bg-blue-600 hover:bg-blue-700 border-blue-600 hover:border-blue-700 text-white'
                        : ((!userInput.trim() || hasUploadingImages || isDocumentProcessing || hasFailedDocuments) ? 'bg-button-disabled border-button-disabled text-white/100 cursor-not-allowed shadow-none hover:shadow-none' : 'bg-button-active hover:bg-[rgb(178,87,53)] border-button-active hover:border-[rgb(178,87,53)] text-white')
                    ]"
                    :title="isDocumentProcessing ? '文档处理中，请稍候...' : hasFailedDocuments ? '存在失败的文档' : hasUploadingImages ? '图片上传中，请稍候...' : ''"
                  >
                    <!-- 上传/处理中提示 -->
                    <svg v-if="hasUploadingImages || isDocumentProcessing" class="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    
                    <svg v-else-if="isLoading" class="w-4 h-4" viewBox="0 0 12 12" fill="currentColor">
                        <rect width="12" height="12" rx="1.5" />
                    </svg>
                    
                    <ArrowUpIcon v-else class="w-5 h-5" />
                  </button>
                </div>
              </div>
            </form>

            <input 
              ref="imageInput"
              type="file" 
              accept="image/*" 
              multiple
              @change="handleImageUpload" 
              class="hidden"
            />
            
            <input 
              ref="fileInput"
              type="file" 
              accept=".pdf"
              @change="handleFileUpload" 
              class="hidden"
            />
          </div>

          <div class="text-center mt-3">
            <p class="text-xs text-text-secondary">
              ViewRAG 正在使用AI知识直接回答，可能会出错，请核实重要信息。
              <button class="text-blue-600 hover:text-blue-700 underline transition-colors duration-200">
                了解更多
              </button>
            </p>
          </div>
        </div>
      </div>
    </main>
    
    <!-- 上传菜单（固定定位，避免被overflow-hidden裁剪） -->
    <div 
      v-if="showMenuDropdown"
      ref="uploadMenu"
      class="fixed bg-white rounded-2xl shadow-xl border border-gray-200 py-2 z-[9999] w-auto"
      :style="uploadMenuStyle"
      @click.stop
    >
      <!-- 上传文档 -->
      <button
        type="button"
        @click="triggerFileUpload"
        class="w-full px-4 py-2 text-left flex items-center gap-3 hover:bg-gray-50 transition-colors duration-150 text-sm text-text-primary whitespace-nowrap"
      >
        <DocumentPlusIcon class="w-5 h-5 text-gray-700 flex-shrink-0" />
        <span class="font-normal">上传文档</span>
      </button>
      
      <!-- 上传图片 -->
      <button
        type="button"
        @click="triggerImageUploadFromMenu"
        :disabled="!isMultiModalModel"
        class="w-full px-4 py-2 text-left flex items-center gap-3 hover:bg-gray-50 transition-colors duration-150 text-sm whitespace-nowrap"
        :class="{
          'text-text-primary cursor-pointer': isMultiModalModel,
          'text-gray-300 cursor-not-allowed': !isMultiModalModel
        }"
      >
        <PhotoIcon class="w-5 h-5 flex-shrink-0" :class="{'text-gray-700': isMultiModalModel, 'text-gray-300': !isMultiModalModel}" />
        <span class="font-normal">上传图片</span>
      </button>
    </div>

    <!-- @ 知识库选择浮动列表 -->
    <div
      v-if="showKbSelector"
      id="kb-selector-popup"
      class="fixed bg-white rounded-xl shadow-xl border border-gray-200 py-1 z-[9999] max-h-64 overflow-y-auto"
      :style="kbSelectorStyle"
      @click.stop
    >
      <div class="px-3 py-2 text-xs text-text-secondary border-b border-gray-100 font-medium">选择知识库</div>
      
      <!-- 加载中 -->
      <div v-if="kbLoading" class="px-4 py-3 flex items-center justify-center gap-2 text-sm text-text-secondary">
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        加载中...
      </div>

      <!-- 空列表 -->
      <div v-else-if="kbList.length === 0" class="px-4 py-3 text-sm text-text-secondary text-center">
        暂无知识库
      </div>

      <!-- 知识库列表 -->
      <button
        v-else
        v-for="kb in kbList"
        :key="kb.id"
        type="button"
        @click="selectKb(kb)"
        class="w-full px-3 py-2 text-left flex items-center gap-2 hover:bg-blue-50 transition-colors duration-150 text-sm"
      >
        <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
        </svg>
        <div class="flex-1 min-w-0">
          <div class="truncate text-text-primary font-medium">{{ kb.name }}</div>
          <div v-if="kb.description" class="truncate text-xs text-text-secondary">{{ kb.description }}</div>
        </div>
        <span class="text-xs text-text-secondary flex-shrink-0">{{ kb.document_count || 0 }} 文档</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue';
import api from '@/services/api';
import ChatSidebar from '@/components/ChatSidebar.vue';
import ChatMessage from '@/components/ChatMessage.vue';
import ModelSelector from '@/components/ModelSelector.vue';
import IconSpinner from '@/components/IconSpinner.vue';
import {
  ArrowUpIcon,
  Bars3Icon,
  DocumentPlusIcon,
  PhotoIcon
} from '@heroicons/vue/24/outline';
import { useRouter } from 'vue-router';
import imageCompression from 'browser-image-compression';
import { useChatReferences } from '@/composables/useChatReferences.js';
import { mockChatStream } from '@/mock/mockChatStream.js';
import { STATUS_PROGRESS_MAP, getKnowledgeBases } from '@/api/knowledgeBase.js';
import SessionFilePanel from '@/components/chat/SessionFilePanel.vue';

// Mock 模式开关：设为 true 时使用 Mock 数据，不依赖后端
const USE_MOCK = false;


const userId = sessionStorage.getItem('userId') || '';

defineEmits(['logout']);

const sessions = ref([]);
const currentSessionId = ref(null);
const messages = ref([]);
const userInput = ref('');

const isLoading = ref(false);
const isSidebarOpen = ref(true);
// 玩偶状态：'idle' | 'thinking' | 'answering'
const mascotStatus = ref('idle');

// 模型选择相关
const availableModels = ref([]);
const selectedModel = ref(null);
const currentSearchSteps = ref([]);
const pendingScenario = ref(null); // 'direct' | 'retrieval' | null
const messagesContainer = ref(null);
const textareaRef = ref(null);
const imageInput = ref(null);
const fileInput = ref(null);
const pendingImages = ref([]); // O.G. uploadedImages. Stores { id, file, blob, previewUrl }
const sessionDocuments = ref([]); // 待发送的文档列表 { doc_id, file_name, status, error_message, progress, step }
const allSessionDocuments = ref([]); // 会话的所有已完成文档（用于右上角面板显示）
const isDragging = ref(false);
const userHasScrolledUp = ref(false); // 用户是否手动上滑
const showMenuDropdown = ref(false);
const uploadMenuButton = ref(null);
const uploadMenu = ref(null);
const uploadMenuStyle = ref({});
const inputAreaRef = ref(null); // 输入框区域容器
const dynamicPaddingBottom = ref('288px'); // 动态底部内边距，默认288px

// @ 知识库选择相关
const showKbSelector = ref(false);
const kbList = ref([]);
const selectedKbId = ref(null);
const selectedKbName = ref('');
const kbSelectorStyle = ref({});
const kbLoading = ref(false);
// const isUploadingImage = ref(false); // No longer needed
// const minioImageUrls = ref([]); // No longer needed, URLs are handled server-side

// 判断当前选择的模型是否为多模态模型
const isMultiModalModel = computed(() => {
  return selectedModel.value?.type === 'multi-model';
});

const router = useRouter();


const abortController = ref(null);
const editingMessageIndex = ref(null);
const retryPayload = ref(null);
// 发送并发与去重保护
const sendLock = ref(false);
const lastSendSignature = ref('');
const lastSendTime = ref(0);

// 引用状态管理（每条消息独立管理引用状态）
const chatReferences = useChatReferences();
// Mock 模式下的 abort 控制器
let mockStreamController = null;

const initAssistantStreamState = (message) => {
  if (!message) return;
  message.rawChunks = [];
  message._streamLogged = false;
};

const appendAssistantStreamChunk = (message, chunk) => {
  if (!message || typeof chunk !== 'string') return;
  if (!Array.isArray(message.rawChunks)) {
    message.rawChunks = [];
  }
  message.rawChunks.push(chunk);
};

const finalizeAssistantStreamLog = (message, context = '') => {
  if (!message || message._streamLogged) return;
  const label = context ? ` ${context}` : '';
  if (Array.isArray(message.rawChunks) && message.rawChunks.length > 0) {
    const fullResponse = message.rawChunks.join('');
    console.log(`[Stream][complete${label}] full response:`, fullResponse);
  } else {
    console.log(`[Stream][complete${label}] no chunks captured; final content:`, message.content);
  }
  message.rawChunks = [];
  message._streamLogged = true;
};

/**
 * 为消息构建引用相关的 Map 数据（referencesMap 和 imageMapping）
 * 用于传递给 ChatMessage 组件
 * @param {Object} message - 消息对象，需包含 references 数组
 */
const buildReferenceMaps = (message) => {
  if (!message || !Array.isArray(message.references)) {
    message._referencesMap = new Map();
    message._imageMapping = new Map();
    return;
  }

  const refMap = new Map();
  const imgMap = new Map();

  for (const item of message.references) {
    refMap.set(item.ref_id, item);
    if (item.chunk_type === 'IMAGE' && item.image_alias && item.image_url) {
      const url = item.image_url.startsWith('/api/')
        ? `/backend${item.image_url}`
        : item.image_url;
      imgMap.set(item.image_alias, url);
    }
  }

  message._referencesMap = refMap;
  message._imageMapping = imgMap;
};

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

// 处理滚动事件，检测用户是否上滑
const handleScroll = () => {
  const container = messagesContainer.value;
  if (!container) return;
  
  const { scrollTop, scrollHeight, clientHeight } = container;
  // 阈值设为 50px，即距离底部超过 50px 视为用户上滑
  const distanceToBottom = scrollHeight - scrollTop - clientHeight;
  userHasScrolledUp.value = distanceToBottom > 50;
};

const scrollToBottom = (force = false) => {
  nextTick(() => {
    if (messagesContainer.value) {
      // 如果强制滚动，或者是用户没有上滑的状态，则执行滚动
      if (force || !userHasScrolledUp.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
      }
    }
  });
};

const autoGrowTextarea = () => {
  nextTick(() => {
    const textarea = textareaRef.value;
    if (textarea) {
      textarea.style.height = 'auto';
      const maxHeight = 144; // 最大高度为144px（约6行）
      if (textarea.scrollHeight <= maxHeight) {
        textarea.style.height = `${textarea.scrollHeight}px`;
      } else {
        textarea.style.height = `${maxHeight}px`;
      }
    }
  });
};

/**
 * 专为AI视觉模型优化的图片压缩函数
 * @param {File} file 原始图片文件
 * @returns {Promise<File>} 压缩后的图片文件 (Blob)
 */
async function compressImageForAI(file) {
  const options = {
    maxSizeMB: 0.5,           // 目标体积: 小于 500KB
    maxWidthOrHeight: 1280,   // 目标尺寸: 小于 1280px
    useWebWorker: false,      // 禁用WebWorker以解决Docker/Build环境下可能的路径加载延迟问题
    fileType: 'image/webp',     // 优先转换为高效的WebP格式
    initialQuality: 0.7,        // 初始压缩质量
  };

  try {
    const compressedFile = await imageCompression(file, options);
    console.log(`图片压缩成功: ${file.name} -> ${compressedFile.name}, 大小: ${Math.round(compressedFile.size / 1024)}KB`);
    return compressedFile;
  } catch (error) {
    console.error(`图片压缩失败: ${file.name}, 将使用原图.`, error);
    showToast(`图片 ${file.name} 压缩失败，将尝试使用原图`, 'error');
    return file; // 压缩失败则返回原图
  }
}

// 图片上传相关
const triggerImageUpload = () => {
  if (isMultiModalModel.value && imageInput.value) {
    imageInput.value.click();
  }
};

const handleImageUpload = (event) => {
  const files = Array.from(event.target.files);
  if (files.length > 0) {
    processImageFiles(files);
  }
};

// 处理粘贴事件
const handlePaste = async (event) => {
  const items = event.clipboardData?.items;
  if (!items) return;
  
  const imageFiles = [];
  
  // 遍历剪贴板项目，查找图片
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    
    // 检查是否为图片类型
    if (item.type.startsWith('image/')) {
      event.preventDefault(); // 阻止默认粘贴行为（避免粘贴图片的文件路径）
      
      const file = item.getAsFile();
      if (file) {
        imageFiles.push(file);
      }
    }
  }
  
  // 如果有图片，处理它们
  if (imageFiles.length > 0) {
    // 检查是否为多模态模型
    if (!isMultiModalModel.value) {
      showToast('图片粘贴需要选择多模态模型，请在右下角切换模型', 'error');
      return;
    }
    
    await processImageFiles(imageFiles);
    showToast(`成功粘贴 ${imageFiles.length} 张图片`, 'success');
  }
};

const processImageFiles = async (files) => {
  const imageFiles = files.filter(f => f.type.startsWith('image/'));
  
  if (imageFiles.length === 0) {
    return;
  }
  
  if (pendingImages.value.length + imageFiles.length > 5) {
    showToast(`最多只能上传5张图片，当前已有${pendingImages.value.length}张`, 'error');
    return;
  }
  
  for (const file of imageFiles) {
    const id = Date.now() + Math.random();

    // 压缩图片
    const compressedBlob = await compressImageForAI(file);
    
    // 生成本地预览URL
    const previewUrl = URL.createObjectURL(compressedBlob);

    pendingImages.value.push({
      id,
      file, // a.k.a original file
      blob: compressedBlob,
      previewUrl,
    });
  }
  
  // 清空文件输入，以便可以再次选择相同的文件
  if (imageInput.value) {
    imageInput.value.value = '';
  }
};

// 上传单张图片 (This function is now obsolete and will be removed)
/*
const uploadSingleImage = async (imageId, imageBase64, filename) => {
...
};
*/

// 新增：显示Toast提示
const showToast = (message, type = 'info') => {
  // 创建toast元素
  const toast = document.createElement('div');
  // 增加 pr-10 为关闭按钮留空间
  toast.className = `fixed top-4 right-4 px-6 py-3 pr-10 rounded-lg shadow-lg z-50 transition-all duration-300 ${
    type === 'success' ? 'bg-green-500 text-white' : 
    type === 'error' ? 'bg-red-500 text-white' : 
    'bg-blue-500 text-white'
  }`;
  
  // 消息文本
  const textSpan = document.createElement('span');
  textSpan.textContent = message;
  toast.appendChild(textSpan);

  // 关闭按钮
  const closeBtn = document.createElement('button');
  closeBtn.innerHTML = '&times;';
  // 修改为 absolute right-1 top-1 定位在右上角
  closeBtn.className = 'absolute right-1 top-1 text-white hover:text-gray-200 focus:outline-none text-xl leading-none px-2 py-1 font-bold cursor-pointer';
  toast.appendChild(closeBtn);

  toast.style.opacity = '0';
  toast.style.transform = 'translateY(-20px)';
  
  document.body.appendChild(toast);
  
  // 动画显示
  setTimeout(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  }, 10);
  
  const removeToast = () => {
    if (!toast.parentElement) return;
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-20px)';
    setTimeout(() => {
      if (toast.parentElement) document.body.removeChild(toast);
    }, 300);
  };

  // 绑定关闭事件
  closeBtn.onclick = (e) => {
    e.stopPropagation();
    clearTimeout(autoRemoveTimer);
    removeToast();
  };
  
  // 2秒后淡出并移除
  const autoRemoveTimer = setTimeout(() => {
    removeToast();
  }, 2000);
};

const removeImage = (imageId) => {
  if (imageId) {
    const index = pendingImages.value.findIndex(img => img.id === imageId);
    if (index !== -1) {
      const removedImg = pendingImages.value.splice(index, 1)[0];
      // 释放之前创建的Object URL
      URL.revokeObjectURL(removedImg.previewUrl);
    }
  } else {
    // 清空所有图片并释放所有Object URL
    pendingImages.value.forEach(img => URL.revokeObjectURL(img.previewUrl));
    pendingImages.value = [];
  }
  
  if (imageInput.value) {
    imageInput.value.value = '';
  }
};

// 移除会话文档（调用后端删除 + 清理前端状态）
const removeSessionDocument = async (docId) => {
  const idx = sessionDocuments.value.findIndex(d => d.doc_id === docId);
  if (idx === -1) return;

  const fileName = sessionDocuments.value[idx].file_name;

  // 1. 关闭 SSE 连接
  if (sseConnections.value[docId]) {
    sseConnections.value[docId].close();
    delete sseConnections.value[docId];
  }

  // 2. 先从前端移除（即时响应）
  sessionDocuments.value.splice(idx, 1);
  const allIdx = allSessionDocuments.value.findIndex(d => d.doc_id === docId);
  if (allIdx !== -1) {
    allSessionDocuments.value.splice(allIdx, 1);
  }

  // 3. 调用后端删除（MinIO 文件 + 数据库记录 + Chunk）
  try {
    await api.deleteSessionDocument(currentSessionId.value, docId);
    console.log(`[Doc] 文档已删除: ${fileName} (${docId})`);
  } catch (error) {
    console.error(`[Doc] 删除文档失败: ${fileName}`, error);
    showToast(`删除文档 ${fileName} 失败: ${error.message || '未知错误'}`, 'error');
  }
};

// 计算上传状态
const hasUploadingImages = computed(() => {
  // This logic is no longer relevant as uploading happens on send
  return false; 
});

// 文档处理状态 computed
const isDocumentProcessing = computed(() => {
  return sessionDocuments.value.some(d =>
    d.status !== 'COMPLETED' && d.status !== 'FAILED'
  );
});

const hasFailedDocuments = computed(() => {
  return sessionDocuments.value.some(d => d.status === 'FAILED');
});

const showFilePanel = ref(false);

const completedDocuments = computed(() => {
  return sessionDocuments.value.filter(d => d.status === 'COMPLETED');
});

// 待处理或已完成的文档（不包括失败的，用于输入框上方显示）
const pendingOrCompletedDocuments = computed(() => {
  return sessionDocuments.value.filter(d => d.status !== 'FAILED');
});

// 加载会话文档列表
const fetchSessionDocuments = async (sessionId) => {
  if (!sessionId) return;
  try {
    const response = await api.getSessionDocuments(sessionId);
    const docs = response.data.documents || [];
    
    // 所有已完成的文档（用于右上角面板显示）
    allSessionDocuments.value = docs
      .filter(d => d.status === 'COMPLETED')
      .map(d => ({
        doc_id: d.id,
        file_name: d.file_name,
        document_type: d.document_type,
        status: d.status,
      }));
    
    // 只加载未绑定消息的已完成文档（message_id 为 null，用于输入框上方显示）
    sessionDocuments.value = docs
      .filter(d => d.status === 'COMPLETED' && !d.message_id)
      .map(d => ({
        doc_id: d.id,
        file_name: d.file_name,
        document_type: d.document_type,
        status: d.status,
        progress: 100,
        step: '已完成'
      }));
    
    console.log(`[Session] 加载会话文档: 全部=${allSessionDocuments.value.length}, 待发送=${sessionDocuments.value.length}`);
  } catch (error) {
    console.error('加载会话文档失败:', error);
    sessionDocuments.value = [];
    allSessionDocuments.value = [];
  }
};

// 拖拽上传相关
let dragCounter = 0; // 用于跟踪拖拽进入/离开事件

const handleDragEnter = (e) => {
  dragCounter++;
  isDragging.value = true;
};

const handleDragOver = (e) => {
  isDragging.value = true;
};

const handleDragLeave = (e) => {
  dragCounter--;
  // 只有当完全离开应用窗口时才隐藏提示
  if (dragCounter === 0) {
    isDragging.value = false;
  }
};

const handleDrop = async (e) => {
  dragCounter = 0;
  isDragging.value = false;
  
  const files = Array.from(e.dataTransfer.files);
  if (files.length === 0) return;
  
  // 分类文件
  const imageFiles = files.filter(f => f.type.startsWith('image/'));
  const documentFiles = files.filter(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    return ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'pptx'].includes(ext);
  });
  
  // 处理图片文件
  if (imageFiles.length > 0) {
    if (!isMultiModalModel.value) {
      showToast('图片上传需要选择多模态模型，请在右下角切换模型', 'error');
      return;
    }
    await processImageFiles(imageFiles);
  }
  
  // 处理文档文件
  if (documentFiles.length > 0) {
    // 构造一个模拟的 event 对象传给 handleFileUpload
    const dataTransfer = new DataTransfer();
    documentFiles.forEach(file => dataTransfer.items.add(file));
    await handleFileUpload({ target: { files: dataTransfer.files } });
  }
  
  // 如果没有支持的文件
  if (imageFiles.length === 0 && documentFiles.length === 0) {
    showToast('不支持的文件格式，请上传文档（PDF、Word、Excel、PPT、TXT）或图片（PNG、JPG、GIF、WebP）', 'error');
  }
};

const fetchMessages = async (sessionId) => {
  // Mock 模式：加载 Mock 历史消息
  if (USE_MOCK) {
    const { getMockHistoryMessages } = await import('@/mock/mockReferences.js');
    const mockMessages = getMockHistoryMessages();
    messages.value = mockMessages.map((m, index) => {
      const msg = {
        ...m,
        message_id: m.message_id || `mock-${sessionId}-${index}`,
        streamEnded: true,
      };
      // 历史消息中的 assistant 消息：立即激活引用交互
      if (msg.role === 'assistant' && msg.references && msg.references.length > 0) {
        msg.isInteractive = true;
        buildReferenceMaps(msg);
        // 检查源文档是否可用
        for (const ref of msg.references) {
          if (!ref.doc_id || !ref.file_name) {
            ref._unavailable = true;
          }
        }
      }
      return msg;
    });
    scrollToBottom();
    return;
  }

  try {
    const response = await api.getMessages(sessionId);
    messages.value = response.data.map((m, index) => {
      // 为从数据库加载的消息生成稳定的前端ID
      const frontendId = `loaded-${sessionId}-${index}-${m.message_id}`;
      
      // 用户消息：保留所有字段
      if (m.role === 'user') {
        return {
          message_id: frontendId,      // 前端稳定ID
          db_message_id: m.message_id, // 数据库真实ID
          role: 'user',
          content: m.content,
          image_url: m.image_url,
          attached_documents: m.attached_documents || [],  // 关联的文档
          timestamp: m.timestamp,
          streamEnded: true  // 历史消息标记为已完成
        };
      }
      
      console.log(`[Debug] 2. 正在处理AI消息 (index: ${index}):`, JSON.parse(JSON.stringify(m)));

      try {
        let parsedContent;
        if (typeof m.content === 'string') {
          try {
            parsedContent = JSON.parse(m.content);
            console.log(`[Debug] 3. 成功将消息内容解析为JSON对象:`, JSON.parse(JSON.stringify(parsedContent)));
          } catch (e) {
            console.log(`[Debug] 3. 消息内容不是一个有效的JSON字符串，将作为纯文本处理。内容:`, m.content);
            parsedContent = m.content;
          }
        } else {
          parsedContent = m.content;
          console.log(`[Debug] 3. 消息内容已经是对象类型:`, JSON.parse(JSON.stringify(parsedContent)));
        }

        let finalContent = '';
        let finalReferences = [];
        let finalRetrievedDocuments = [];

        if (typeof parsedContent === 'object' && parsedContent !== null) {
          if (parsedContent.text) {
            finalContent = parsedContent.text;
            console.log(`[Debug] 4. 从解析后的对象中提取 'text' 属性作为最终内容。`);
          } else {
            console.warn(`[Debug] 4. 警告：解析后的对象没有 'text' 属性，内容将为空。对象:`, JSON.parse(JSON.stringify(parsedContent)));
          }
          finalReferences = parsedContent.references || [];
          finalRetrievedDocuments = parsedContent.retrieved_documents || [];
        } else if (typeof parsedContent === 'string') {
          finalContent = parsedContent;
          console.log(`[Debug] 4. 内容是纯字符串，直接作为最终内容。`);
        }

        const finalMessageObject = { 
          message_id: frontendId,
          db_message_id: m.message_id,
          role: 'assistant', 
          content: finalContent, 
          references: finalReferences,
          retrieved_documents: finalRetrievedDocuments,
          isInteractive: finalReferences.length > 0,  // 历史消息立即激活引用交互
          streamEnded: true  // 历史消息标记为已完成流式传输
        };
        
        // 如果有思考过程，添加到消息对象
        if (m.thinking_content) {
          finalMessageObject.thinking_content = m.thinking_content;
          finalMessageObject.isThinking = false;
          finalMessageObject.thinkingDone = true;  // 历史消息的思考已完成
        }
        
        // 构建引用 Map 数据
        buildReferenceMaps(finalMessageObject);
        // 处理源文档已删除的情况：检查引用是否有效
        if (finalReferences.length > 0) {
          for (const ref of finalReferences) {
            if (!ref.doc_id || !ref.file_name) {
              ref._unavailable = true;
            }
          }
        }
        console.log(`[Debug] 5. 最终生成并推入渲染数组的消息对象:`, JSON.parse(JSON.stringify(finalMessageObject)));
        return finalMessageObject;

      } catch (e) {
        console.error(`[Debug] X. 处理消息时发生未知错误:`, e);
        const errorObject = { 
          message_id: frontendId,
          db_message_id: m.message_id,
          role: 'assistant', 
          content: `加载此条消息时出错: ${String(m.content)}`, 
          references: [] 
        };
        console.log(`[Debug] X. 返回错误消息对象:`, JSON.parse(JSON.stringify(errorObject)));
        return errorObject;
      }
    });
      // AI消息：解析content
    //   try {
    //     let content = typeof m.content === 'string' ? JSON.parse(m.content) : m.content;
    //     if (typeof content.text === 'string') {
    //       try {
    //         const nestedContent = JSON.parse(content.text);
    //         if (typeof nestedContent.text !== 'undefined') content = nestedContent;
    //       } catch (e) {  }
    //     }
    //     return { 
    //       message_id: frontendId,      // 前端稳定ID
    //       db_message_id: m.message_id, // 数据库真实ID
    //       role: 'assistant', 
    //       content: content.text || '', 
    //       references: content.references || [] 
    //     };
    //   } catch (e) {
    //     return { 
    //       message_id: frontendId,
    //       db_message_id: m.message_id,
    //       role: 'assistant', 
    //       content: String(m.content), 
    //       references: [] 
    //     };
    //   }
    // });
    scrollToBottom();
  } catch (error) {
    console.error("加载消息时出错:", error);
    messages.value = [{ 
      message_id: `error-${Date.now()}`,
      role: 'assistant', 
      content: '加载历史消息失败。' 
    }];
  }
};

const selectSession = async (sessionId) => {
  if (isLoading.value || currentSessionId.value === sessionId) return;
  currentSessionId.value = sessionId;
  messages.value = [];
  // When switching sessions, clear any pending images and session documents
  removeImage(null);
  sessionDocuments.value = [];
  allSessionDocuments.value = [];
  showFilePanel.value = false;
  selectedKbId.value = null;
  selectedKbName.value = '';
  // 清理 SSE 连接
  closeAllSSEConnections();
  isLoading.value = true;
  try {
    await fetchMessages(sessionId);
    // 加载会话已有的文档列表
    await fetchSessionDocuments(sessionId);
  } finally {
    isLoading.value = false;
    // 切换会话后自动聚焦输入框
    nextTick(() => textareaRef.value?.focus());
  }
};

const fetchSessions = async () => {
  if (USE_MOCK) {
    // Mock 模式：创建一个默认会话
    const mockSessionId = `mock-session-default`;
    sessions.value = [{
      session_id: mockSessionId,
      title: 'Transformer 注意力机制',
      created_at: new Date().toISOString()
    }];
    if (!currentSessionId.value) {
      await selectSession(mockSessionId);
    }
    return;
  }

  try {
    const response = await api.getSessions(userId);
    sessions.value = response.data;
    if (sessions.value.length > 0 && !currentSessionId.value) {
      await selectSession(sessions.value[0].session_id);
    }
  } catch (error) {
    console.error("加载会话列表时出错:", error);
  }
};

/**
 * 异步调用后端 LLM 生成会话摘要标题，并更新侧边栏显示。
 * 不阻塞主流程，失败时静默处理。
 */
const generateAndUpdateTitle = async (sessionId) => {
  try {
    // 记录当前临时标题，用于判断是否已被 LLM 更新
    const currentSession = sessions.value.find(s => s.session_id === sessionId);
    const tempTitle = currentSession?.title || '';
    
    // 触发后端异步生成标题
    await api.generateSessionTitle(sessionId);
    
    // 轮询获取生成后的标题（最多等待 15 秒）
    const maxAttempts = 7;
    const interval = 2000;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, interval));
      try {
        const res = await api.getSessionTitle(sessionId);
        const newTitle = res.data?.title;
        // 只要后端返回了标题且与临时标题不同，就认为 LLM 已生成
        if (newTitle && newTitle !== tempTitle) {
          const session = sessions.value.find(s => s.session_id === sessionId);
          if (session) {
            session.title = newTitle;
          }
          console.log('[Chat] 会话标题已更新:', newTitle);
          return;
        }
      } catch (e) {
        // 轮询失败，继续尝试
      }
    }
    console.warn('[Chat] 轮询超时，标题可能未更新');
  } catch (error) {
    console.warn('[Chat] 生成会话标题失败，使用默认标题:', error);
  }
};

const createNewSession = async () => {
  if (isLoading.value) return;
  currentSessionId.value = null;
  messages.value = [];
  removeImage(null); // New session should not have pending images
  sessionDocuments.value = [];
  allSessionDocuments.value = [];
  selectedKbId.value = null;
  selectedKbName.value = '';
  // 清理 SSE 连接
  closeAllSSEConnections();
  nextTick(() => textareaRef.value?.focus());
};

const handleStop = () => {
  console.log('[Chat] 用户点击停止按钮, isLoading=', isLoading.value);
  
  // 1. 中断网络请求
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }
  
  // 1.1 中断 Mock 流
  if (mockStreamController) {
    mockStreamController.abort();
    mockStreamController = null;
  }
  
  // 2. 立即重置状态（关键！防止卡死）
  isLoading.value = false;
  mascotStatus.value = 'idle';
  sendLock.value = false;
  
  // 3. 清理搜索步骤
  currentSearchSteps.value = [];
  
  // 4. 确保最后一条消息有正确的状态
  const lastMsg = messages.value[messages.value.length - 1];
  if (lastMsg && lastMsg.role === 'assistant') {
    // 如果还没有内容，显示"已停止"
    if (!lastMsg.content || lastMsg.content.trim() === '') {
      lastMsg.content = '回答已停止。';
    }
    lastMsg.streamEnded = true;  // 标记为已结束
  }
  
  // 5. 重置引用状态
  chatReferences.reset();
  
  console.log('[Chat] 停止完成，isLoading=', isLoading.value);
};

const sendMessage = async () => {
  console.log('[Chat] sendMessage called. isLoading=', isLoading.value, 'sendLock=', sendLock.value, 'userInput=', userInput.value);
  
  // 防御性检查：如果状态异常，先重置
  if (isLoading.value && !abortController.value) {
    console.warn('[Chat] 检测到状态异常：isLoading=true 但没有活动请求，重置状态');
    isLoading.value = false;
    sendLock.value = false;
  }
  
  // Guard against sending empty messages, unless there are images
  if (!userInput.value.trim() && pendingImages.value.length === 0) return;
  if (isLoading.value || sendLock.value) {
    console.warn('[Chat] Blocked duplicate send: isLoading or sendLock active');
    return;
  }

  // 短时间内相同内容去重
  const signature = `${userInput.value.trim()}|imgs:${pendingImages.value.map(i => i.previewUrl).join(',')}`;
  const now = Date.now();
  if (signature && signature === lastSendSignature.value && now - lastSendTime.value < 800) {
    console.warn('[Chat] Blocked rapid duplicate by signature');
    return;
  }
  lastSendSignature.value = signature;
  lastSendTime.value = now;
  sendLock.value = true;

  isLoading.value = true;
  mascotStatus.value = 'thinking';
  let sessionIdToUse = currentSessionId.value;

  // 1. Ensure a session exists before sending anything
  let isNewSession = false;
  if (!sessionIdToUse) {
    isNewSession = true;
    if (USE_MOCK) {
      // Mock 模式：生成本地 session ID
      sessionIdToUse = `mock-session-${Date.now()}`;
      currentSessionId.value = sessionIdToUse;
      sessions.value.unshift({
        session_id: sessionIdToUse,
        title: userInput.value.trim().substring(0, 10) || '新对话',
        created_at: new Date().toISOString()
      });
    } else {
      try {
        // 先用截取的文本作为临时标题，后续由 LLM 生成摘要标题
        const tempTitle = userInput.value.trim().substring(0, 10) || '新对话';
        const response = await api.createSession(userId, tempTitle);
        sessionIdToUse = response.data.session_id;
        currentSessionId.value = sessionIdToUse;
        await fetchSessions();
      } catch (error) {
        console.error("创建新会话时出错:", error);
        messages.value.push({ role: 'assistant', content: '创建新会话失败，请重试。' });
        isLoading.value = false;
        sendLock.value = false;
        return;
      }
    }
  }

  const query = userInput.value;
  const hasImages = pendingImages.value.length > 0;
  const hasDocuments = completedDocuments.value.length > 0;
  
  // Add user's message to the UI immediately for better UX
  // 使用稳定的前端ID作为Vue的key，真实的message_id存储在 db_message_id 中
  const tempUserMessageIndex = messages.value.length;
  const frontendId = `frontend-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  const userMessage = { 
    message_id: frontendId,  // 前端稳定ID，用于Vue的key
    db_message_id: null,     // 数据库真实ID，后续会更新
    role: 'user', 
    content: query,
  };
  
  // 只有在有图片时才添加 image_url 字段
  if (hasImages) {
    userMessage.image_url = pendingImages.value.map(img => img.previewUrl);
  }
  
  // 附加已完成的文档到用户消息
  if (hasDocuments) {
    userMessage.attached_documents = completedDocuments.value.map(doc => ({
      doc_id: doc.doc_id,
      file_name: doc.file_name,
      document_type: doc.document_type || null
    }));
  }
  
  messages.value.push(userMessage);
  
  // Prepare for assistant's response
  const frontendAssistantId = `frontend-assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const assistantMessage = {
    message_id: frontendAssistantId,
    db_message_id: null,
    role: 'assistant',
    content: '',
    references: [],
    retrieved_documents: [],
    streamEnded: false,
    thinking_content: '',
    isThinking: false,
    thinkingDone: false,
  };
  initAssistantStreamState(assistantMessage);
  messages.value.push(assistantMessage);
  currentSearchSteps.value = [];
  
  // 判断场景并设置等待提示
  if (selectedKbId.value || allSessionDocuments.value.length > 0) {
    pendingScenario.value = 'retrieval';
  } else {
    pendingScenario.value = 'direct';
  }
  
  scrollToBottom(true); // 发送新消息时强制滚动到底部
  // 重置上滑状态
  userHasScrolledUp.value = false;

  // 2. 保存用户消息到数据库（有图片或无图片）

  // 【优化】缓存待发送数据并在发送请求前立即清理UI，解决发送后图片滞留问题
  const imagesToSend = [...pendingImages.value];
  const documentsToSend = hasDocuments ? [...completedDocuments.value] : [];

  // 立即清空预览区域 (注意：暂不revoke URL，因为消息列表还在引用这些 Blob URL)
  pendingImages.value = [];
  
  if (hasDocuments) {
    // 移除已完成的文档（已绑定到当前消息）
    sessionDocuments.value = sessionDocuments.value.filter(d => d.status !== 'COMPLETED');
  }
  
  // 立即清空输入框
  userInput.value = '';
  nextTick(() => {
    if (textareaRef.value) textareaRef.value.style.height = 'auto';
  });

  if (USE_MOCK) {
    // Mock 模式已在上方清理完毕
  } else {
    try {
      const formData = new FormData();
      formData.append('text', query);
      formData.append('session_id', sessionIdToUse);
      formData.append('user_id', userId);
      
      // 使用缓存的 imagesToSend
      if (hasImages) {
        imagesToSend.forEach(img => {
          formData.append('images', img.blob, 'image.webp');
        });
      }
      
      // 使用缓存的 documentsToSend
      if (hasDocuments) {
        const docIds = documentsToSend.map(doc => doc.doc_id);
        formData.append('doc_ids', JSON.stringify(docIds));
      }

      console.log('[Chat] Calling sendMessageWithImages');
      const response = await api.sendMessageWithImages(formData);
      console.log('[Chat] sendMessageWithImages resp:', response);
      
      if (response.message_id && messages.value[tempUserMessageIndex]) {
        messages.value[tempUserMessageIndex].db_message_id = response.message_id;
        console.log('[Chat] Saved db_message_id:', response.message_id, 'frontend_id:', messages.value[tempUserMessageIndex].message_id);
        
        // 用后端返回的代理 URL 替换本地 blob URL，确保刷新后图片仍可访问
        if (response.image_urls && response.image_urls.length > 0) {
          messages.value[tempUserMessageIndex].image_url = response.image_urls;
          
          // 替换成功后，释放之前的 Blob URL 资源
          imagesToSend.forEach(img => URL.revokeObjectURL(img.previewUrl));
        }
      }
      
      // 原清理代码已移至顶部

    } catch (error) {
      console.error("保存用户消息失败:", error);
      messages.value[messages.value.length - 1].content = `发送消息失败: ${error.message}`;
      messages.value[messages.value.length - 1].streamEnded = true;
      isLoading.value = false;
      return;
    }
  }

  // 3. 获取 AI 响应（Mock 模式或真实 API）
  if (USE_MOCK) {
    // Mock 模式：使用 mockChatStream 模拟 SSE 流
    chatReferences.reset();
    const assistantMsg = messages.value[messages.value.length - 1];
    
    console.log('[Chat][Mock] 开始 Mock 流式响应');
    mockStreamController = mockChatStream(query, {
      onRetrievedDocs(docs) {
        // 缓存召回文档列表
        if (assistantMsg) {
          assistantMsg.retrieved_documents = docs;
        }
        console.log('[Chat][Mock] 收到 retrieved_documents:', docs.length, '篇');
      },
      onReferences(refList) {
        // 缓存引用数据并构建图片映射
        chatReferences.handleReferences(refList);
        if (assistantMsg) {
          assistantMsg.references = refList;
          buildReferenceMaps(assistantMsg);
        }
        console.log('[Chat][Mock] 收到 references:', refList.length, '条');
      },
      onToken(token) {
        if (assistantMsg) {
          appendAssistantStreamChunk(assistantMsg, token);
          assistantMsg.content += token;
          // 流式传输中同步 imageMapping 以便图片立即渲染
          assistantMsg._imageMapping = chatReferences.imageMapping.value;
          assistantMsg._referencesMap = chatReferences.references.value;
          scrollToBottom(false); // 流式更新时不强制滚动，尊重用户行为
        }
      },
      onDone() {
        // 激活引用交互
        chatReferences.activateInteraction();
        if (assistantMsg) {
          assistantMsg.streamEnded = true;
          assistantMsg.isInteractive = true;
          buildReferenceMaps(assistantMsg);
          finalizeAssistantStreamLog(assistantMsg, 'mockStream');
        }
        isLoading.value = false;
        sendLock.value = false;
        mockStreamController = null;
        console.log('[Chat][Mock] 流式响应完成');
      },
      onError(error) {
        console.error('[Chat][Mock] 流处理错误:', error);
        isLoading.value = false;
        sendLock.value = false;
        mockStreamController = null;
        if (assistantMsg) {
          assistantMsg.hasError = true;
          assistantMsg.errorMessage = error.message || 'Mock 流处理错误';
          assistantMsg.streamEnded = true;
        }
      }
    });
    // Mock 模式不需要 finally 块，回调中已处理状态重置
    return;
  }

  // 真实 API 模式
  abortController.value = new AbortController();
  const payload = {
    session_id: sessionIdToUse,
    user_id: userId,
    selected_model: selectedModel.value?.name || null,
    query: query,
    kb_id: selectedKbId.value || null,
    has_docs: allSessionDocuments.value.length > 0,
  };

  try {
    let buffer = '';
    let fullResponseText = '';
    const payloadToSend = Object.assign({}, payload);
    if (!payloadToSend.query || payloadToSend.query === '') {
      const lastUser = [...messages.value].reverse().find(m => m.role === 'user');
      payloadToSend.query = lastUser ? lastUser.content : '';
    }
    retryPayload.value = payloadToSend;
    console.log('[Chat] Start searchStream. payload=', payloadToSend);
    await api.searchStream(
      payloadToSend,
      (chunk) => {
        buffer += chunk;
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);
          if (line.trim()) {
            try {
              const chunkData = JSON.parse(line);
              if (chunkData.type === 'answer_chunk') {
                fullResponseText += chunkData.data || '';
              }
            } catch (e) {
              // 忽略解析错误
            }
            processStreamChunk(line);
          }
        }
      },
      () => { // onComplete
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.streamEnded = true;
          lastMsg.isInteractive = (lastMsg.references && lastMsg.references.length > 0);
          buildReferenceMaps(lastMsg);
          finalizeAssistantStreamLog(lastMsg, 'searchStream');
          
          console.log('===== 前端接收 - 完整AI回复开始 =====');
          console.log('完整回复文本:\n', fullResponseText);
          console.log('消息对象content:\n', lastMsg.content);
          console.log('参考来源数量:', lastMsg.references ? lastMsg.references.length : 0);
          console.log('===== 前端接收 - 完整AI回复结束 =====');
        }
        console.log('[Chat] searchStream complete');
      },
      (error) => { // onError
        console.error('流处理错误:', error);
        
        isLoading.value = false;
        sendLock.value = false;
        abortController.value = null;
        
        if (error.name === 'AbortError') {
          console.log('用户主动取消了请求');
          const lastMsg = messages.value[messages.value.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            if (!lastMsg.content || lastMsg.content.trim() === '') {
              lastMsg.content = '回答已停止。';
            }
            lastMsg.streamEnded = true;
            finalizeAssistantStreamLog(lastMsg, 'searchStream abort');
          }
        } else {
          console.error('网络错误:', error);
          const lastMsg = messages.value[messages.value.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.hasError = true;
            lastMsg.errorMessage = error.message || '网络或服务器错误，请稍后再试';
            lastMsg.streamEnded = true;
            finalizeAssistantStreamLog(lastMsg, 'searchStream error');
          }
        }
      },
      abortController.value.signal
    );
  } finally {
    isLoading.value = false;
    mascotStatus.value = 'idle';
    sendLock.value = false;
    abortController.value = null;
    userInput.value = '';
    autoGrowTextarea();
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.streamEnded = true;
      finalizeAssistantStreamLog(lastMsg, 'sendMessage finally');
    }
    
    // 新会话或第一条消息：异步调用 LLM 生成摘要标题，更新侧边栏
    const userMessagesCount = messages.value.filter(m => m.role === 'user').length;
    if ((isNewSession || userMessagesCount === 1) && sessionIdToUse && !USE_MOCK) {
      generateAndUpdateTitle(sessionIdToUse);
    }
    
    console.log('[Chat] sendMessage finished');
  }
};

const processStreamChunk = (line) => {
  // 限制日志大小：仅打印前200字符
  if (typeof line === 'string') {
    const preview = line.length > 200 ? line.slice(0, 200) + ' ...' : line;
    console.debug('[Stream] chunk line:', preview);
  }
  try {
    const chunk = JSON.parse(line);
    const { type, data: payload } = chunk;
    const currentMessage = messages.value[messages.value.length - 1];

    switch (type) {
      case 'thinking_chunk':
        // 推理模型思考过程
        if (currentMessage && currentMessage.role === 'assistant') {
          currentMessage.thinking_content += payload;
          currentMessage.isThinking = true;
          pendingScenario.value = null; // 清除等待提示
          mascotStatus.value = 'answering'; // 收到内容即切换
          scrollToBottom(false);
        }
        break;
      case 'thinking_done':
        // 思考结束
        if (currentMessage && currentMessage.role === 'assistant') {
          currentMessage.isThinking = false;
          currentMessage.thinkingDone = true;
        }
        break;
      case 'answer_chunk':
        if (currentMessage && currentMessage.role === 'assistant') {
          appendAssistantStreamChunk(currentMessage, payload);
          currentMessage.content += payload;
          // 流式传输中同步 imageMapping 以便图片立即渲染
          currentMessage._imageMapping = chatReferences.imageMapping.value;
          currentMessage._referencesMap = chatReferences.references.value;
          pendingScenario.value = null; // 清除等待提示
          mascotStatus.value = 'answering'; // 收到内容即切换
          scrollToBottom(false);
        }
        break;
      case 'reference':
        if (currentMessage && currentMessage.role === 'assistant') {
          currentMessage.references = payload;
          buildReferenceMaps(currentMessage);
        }
        break;
      case 'references':
        // SSE references 事件：缓存引用数据
        if (currentMessage && currentMessage.role === 'assistant' && Array.isArray(payload)) {
          chatReferences.handleReferences(payload);
          currentMessage.references = payload;
          buildReferenceMaps(currentMessage);
          console.log('[Stream] 收到 references 事件:', payload.length, '条');
          console.log('[Stream] references 完整数据:', JSON.parse(JSON.stringify(payload)));
        }
        break;
      case 'retrieved_documents':
        // SSE retrieved_documents 事件：缓存召回文档列表
        if (currentMessage && currentMessage.role === 'assistant' && Array.isArray(payload)) {
          currentMessage.retrieved_documents = payload;
          pendingScenario.value = null; // 清除等待提示
          console.log('[Stream] 收到 retrieved_documents 事件:', payload.length, '篇');
        }
        break;
      case 'done':
        // SSE done 事件：激活引用交互
        if (currentMessage && currentMessage.role === 'assistant') {
          chatReferences.activateInteraction();
          currentMessage.streamEnded = true;
          currentMessage.isInteractive = true;
          buildReferenceMaps(currentMessage);
          console.log('[Stream] 收到 done 事件，引用交互已激活');
        }
        break;
      case 'error':
        if (currentMessage && currentMessage.role === 'assistant') {
          currentMessage.hasError = true;
          currentMessage.errorMessage = payload;
          currentMessage.streamEnded = true;
        }
        break;
    }
  } catch (error) {
    console.error('解析JSON块时出错:', error, '原始数据:', line);
  }
};

// @ 知识库选择：监听输入检测 @ 字符
const handleTextareaInput = (e) => {
  autoGrowTextarea();
  const textarea = textareaRef.value;
  if (!textarea) return;

  const value = textarea.value;
  const cursorPos = textarea.selectionStart;

  // 检测光标前一个字符是否为 @
  if (cursorPos > 0 && value[cursorPos - 1] === '@') {
    openKbSelector();
  }
};

const openKbSelector = async () => {
  // 计算浮动列表位置（在输入框上方）
  if (textareaRef.value) {
    const rect = textareaRef.value.getBoundingClientRect();
    kbSelectorStyle.value = {
      bottom: `${window.innerHeight - rect.top + 8}px`,
      left: `${rect.left}px`,
      minWidth: '240px',
      maxWidth: '360px',
    };
  }
  showKbSelector.value = true;
  kbLoading.value = true;

  try {
    const response = await getKnowledgeBases(userId);
    const data = response.data;
    kbList.value = data.knowledge_bases || data || [];
  } catch (err) {
    console.error('[Chat] 获取知识库列表失败:', err);
    kbList.value = [];
  } finally {
    kbLoading.value = false;
  }
};

const selectKb = (kb) => {
  selectedKbId.value = kb.id;
  selectedKbName.value = kb.name;
  showKbSelector.value = false;

  // 移除输入框中的 @ 字符
  const textarea = textareaRef.value;
  if (textarea) {
    const value = textarea.value;
    const cursorPos = textarea.selectionStart;
    // 找到光标前最近的 @ 并移除
    const beforeCursor = value.substring(0, cursorPos);
    const atIndex = beforeCursor.lastIndexOf('@');
    if (atIndex !== -1) {
      userInput.value = value.substring(0, atIndex) + value.substring(cursorPos);
      nextTick(() => {
        textarea.selectionStart = textarea.selectionEnd = atIndex;
        textarea.focus();
      });
    }
  }
};

const clearSelectedKb = () => {
  selectedKbId.value = null;
  selectedKbName.value = '';
  nextTick(() => textareaRef.value?.focus());
};

const closeKbSelector = () => {
  showKbSelector.value = false;
};

// 点击外部关闭知识库选择列表
const handleKbSelectorClickOutside = (e) => {
  if (showKbSelector.value) {
    const selectorEl = document.getElementById('kb-selector-popup');
    if (selectorEl && !selectorEl.contains(e.target) && !textareaRef.value?.contains(e.target)) {
      showKbSelector.value = false;
    }
  }
};

const handleEnter = (e) => {
  if (!e.shiftKey && !e.isComposing) {
    // 如果知识库选择列表打开，按 Enter 不发送消息，而是关闭列表
    if (showKbSelector.value) {
      showKbSelector.value = false;
      e.preventDefault();
      return;
    }
    console.log('[Chat] handleEnter fired');
    e.preventDefault();
    sendMessage();
  }
};

const handleLogout = () => {
  sessionStorage.clear();
  router.push('/login');
};

const navigateToConfig = () => {
  router.push('/config');
};

const navigateToKnowledgeBase = () => {
  router.push('/knowledge-base');
};

// 处理重新生成
const handleRegenerate = async (message) => {
  if (isLoading.value) return;
  
  const messageIndex = messages.value.findIndex(m => m.message_id === message.message_id);
  if (messageIndex === -1) return;
  
  editingMessageIndex.value = messageIndex;
  messages.value = messages.value.slice(0, messageIndex + 1);
  
  const payload = {
    session_id: currentSessionId.value,
    message_id: message.db_message_id,  // 使用数据库真实ID
    new_query: message.content,
    new_image_urls: message.image_url ? (Array.isArray(message.image_url) ? message.image_url : [message.image_url]) : null,
    selected_model: selectedModel.value?.name || null,
    has_docs: allSessionDocuments.value.length > 0,
  };
  
  // 为新的AI回复生成前端ID
  const frontendAssistantId = `frontend-assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const assistantMessage = {
    message_id: frontendAssistantId,
    db_message_id: null,
    role: 'assistant',
    content: '',
    references: [],
    retrieved_documents: [],
    streamEnded: false,
    thinking_content: '',
    isThinking: false,
    thinkingDone: false,
  };
  initAssistantStreamState(assistantMessage);
  messages.value.push(assistantMessage);
  currentSearchSteps.value = [];
  
  // 判断场景并设置等待提示
  if (selectedKbId.value || allSessionDocuments.value.length > 0) {
    pendingScenario.value = 'retrieval';
  } else {
    pendingScenario.value = 'direct';
  }
  
  isLoading.value = true;
  
  await callRegenerateAPI(payload);
  editingMessageIndex.value = null;
};

// 处理编辑
const handleEdit = async ({ message, newContent, newImages }) => {
  if (isLoading.value) return;
  
  const messageIndex = messages.value.findIndex(m => m.message_id === message.message_id);
  if (messageIndex === -1) return;
  
  editingMessageIndex.value = messageIndex;
  messages.value[messageIndex].content = newContent;
  // 如果 newImages 是空数组，设置为 null，避免显示空的图片区域
  messages.value[messageIndex].image_url = (newImages && newImages.length > 0) ? newImages : null;
  messages.value = messages.value.slice(0, messageIndex + 1);
  
  const payload = {
    session_id: currentSessionId.value,
    message_id: message.db_message_id,  // 使用数据库真实ID
    new_query: newContent,
    new_image_urls: newImages && newImages.length > 0 ? newImages : null,
    selected_model: selectedModel.value?.name || null,
    has_docs: allSessionDocuments.value.length > 0,
  };
  
  // 为新的AI回复生成前端ID
  const frontendAssistantId = `frontend-assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const assistantMessage = {
    message_id: frontendAssistantId,
    db_message_id: null,
    role: 'assistant',
    content: '',
    references: [],
    retrieved_documents: [],
    streamEnded: false,
  };
  initAssistantStreamState(assistantMessage);
  messages.value.push(assistantMessage);
  currentSearchSteps.value = [];
  isLoading.value = true;
  
  await callRegenerateAPI(payload);
  editingMessageIndex.value = null;
};

// 处理重试
const handleRetry = async () => {
  if (!retryPayload.value || isLoading.value) return;
  
  // 核心修复：重试前更新使用的模型（用户可能为了通过兼容性检查而切换了模型）
  if (selectedModel.value?.name) {
    retryPayload.value.selected_model = selectedModel.value.name;
  }
  
  const lastMsg = messages.value[messages.value.length - 1];
  if (lastMsg && lastMsg.hasError) {
    messages.value.pop();
  }
  
  const retryAssistant = { 
    role: 'assistant', 
    content: '', 
    references: [], 
    streamEnded: false,
    thinking_content: '',
    isThinking: false,
    thinkingDone: false,
  };
  initAssistantStreamState(retryAssistant);
  messages.value.push(retryAssistant);
  currentSearchSteps.value = [];
  
  // 判断场景并设置等待提示
  if (selectedKbId.value || allSessionDocuments.value.length > 0) {
    pendingScenario.value = 'retrieval';
  } else {
    pendingScenario.value = 'direct';
  }
  
  isLoading.value = true;
  
  await callSearchAPI(retryPayload.value);
};

// 调用regenerate API
const callRegenerateAPI = async (payload) => {
  abortController.value = new AbortController();
  let fullResponseText = ''; // 收集完整的AI回复文本用于调试
  
  try {
    let buffer = '';
    await api.regenerateStream(
      payload,
      (chunk) => {
        buffer += chunk;
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);
          if (line.trim()) {
            try {
              const chunkData = JSON.parse(line);
              if (chunkData.type === 'answer_chunk') {
                fullResponseText += chunkData.data || '';
              }
            } catch (e) {
              // 忽略解析错误
            }
            processStreamChunk(line);
          }
        }
      },
      () => {
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.streamEnded = true;
          lastMsg.isInteractive = (lastMsg.references && lastMsg.references.length > 0);
          buildReferenceMaps(lastMsg);
          finalizeAssistantStreamLog(lastMsg, 'regenerate');
        }
        isLoading.value = false;
        abortController.value = null;
        
        // 打印前端接收到的完整回复
        console.log('===== 前端接收(重新生成) - 完整AI回复开始 =====');
        console.log('完整回复文本:\n', fullResponseText);
        console.log('消息对象content:\n', lastMsg?.content);
        console.log('参考来源数量:', lastMsg?.references ? lastMsg.references.length : 0);
        console.log('===== 前端接收(重新生成) - 完整AI回复结束 =====');
        
        scrollToBottom();
      },
      (error) => {
        console.error('Regenerate失败:', error);
        
        // 立即重置状态（防止卡死）
        isLoading.value = false;
        sendLock.value = false;
        abortController.value = null;
        
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          if (error.name === 'AbortError') {
            if (!lastMsg.content || lastMsg.content.trim() === '') {
              lastMsg.content = '回答已停止。';
            }
          } else {
            lastMsg.hasError = true;
            lastMsg.errorMessage = error.message || '生成失败，请重试';
          }
          lastMsg.streamEnded = true;
          finalizeAssistantStreamLog(lastMsg, 'regenerate error');
        }
      },
      abortController.value.signal
    );
  } catch (error) {
    console.error('调用regenerate API失败:', error);
    
    // 立即重置状态（防止卡死）
    isLoading.value = false;
    sendLock.value = false;
    abortController.value = null;
    
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.hasError = true;
      lastMsg.errorMessage = error.message || '生成失败，请重试';
      lastMsg.streamEnded = true;
      finalizeAssistantStreamLog(lastMsg, 'regenerate catch');
    }
  }
};

// 调用search API
const callSearchAPI = async (payload) => {
  abortController.value = new AbortController();
  retryPayload.value = payload;
  
  try {
    let buffer = '';
    await api.searchStream(
      payload,
      (chunk) => {
        buffer += chunk;
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);
          if (line.trim()) {
            processStreamChunk(line);
          }
        }
      },
      () => {
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.streamEnded = true;
          lastMsg.isInteractive = (lastMsg.references && lastMsg.references.length > 0);
          buildReferenceMaps(lastMsg);
          finalizeAssistantStreamLog(lastMsg, 'search retry');
        }
        isLoading.value = false;
        abortController.value = null;
        // 成功也不要清空 retryPayload，允许用户再次重试
        scrollToBottom();
      },
      (error) => {
        console.error('Search失败:', error);
        
        // 立即重置状态，不要清空 retryPayload，以便用户再次重试
        isLoading.value = false;
        sendLock.value = false;
        abortController.value = null;
        
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          if (error.name === 'AbortError') {
            if (!lastMsg.content || lastMsg.content.trim() === '') {
              lastMsg.content = '回答已停止。';
            }
          } else {
            lastMsg.hasError = true;
            lastMsg.errorMessage = error.message || '生成失败，请重试';
          }
          lastMsg.streamEnded = true;
          finalizeAssistantStreamLog(lastMsg, 'search retry error');
        }
      },
      abortController.value.signal
    );
  } catch (error) {
    console.error('调用search API失败:', error);
    
    // 立即重置状态（防止卡死）
    isLoading.value = false;
    sendLock.value = false;
    abortController.value = null;
    retryPayload.value = null;
    
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.hasError = true;
      lastMsg.errorMessage = error.message || '生成失败，请重试';
      lastMsg.streamEnded = true;
      finalizeAssistantStreamLog(lastMsg, 'search retry catch');
    }
  }
};

// 获取可用的对话模型列表
const fetchChatModels = async () => {
  try {
    const response = await api.getChatModels();
    if (response.data.success && response.data.models) {
      availableModels.value = response.data.models;
      // 设置默认模型
      const defaultModel = availableModels.value.find(m => m.is_default);
      if (defaultModel) {
        selectedModel.value = defaultModel;
      } else if (availableModels.value.length > 0) {
        selectedModel.value = availableModels.value[0];
      }
      console.log('已加载对话模型列表:', availableModels.value);
      console.log('默认模型:', selectedModel.value);
    }
  } catch (error) {
    console.error('获取对话模型列表失败:', error);
  }
};

// 处理模型选择
const handleModelSelect = (model) => {
  selectedModel.value = model;
  console.log('切换到模型:', model.name);
};

// 触发文件上传
const triggerFileUpload = () => {
  showMenuDropdown.value = false; // 关闭菜单
  if (fileInput.value) {
    fileInput.value.click();
  }
};

// 处理文件上传
const handleFileUpload = async (event) => {
  const files = Array.from(event.target.files);
  if (files.length === 0) return;

  // 目前仅支持 PDF 文档
  const ALLOWED_EXTENSIONS = ['pdf'];
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

  for (const file of files) {
    // 1. 校验文件格式
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      showToast(`目前仅支持 PDF 文档，暂不支持 ${file.name}`, 'error');
      continue;
    }

    // 2. 校验文件大小
    if (file.size > MAX_FILE_SIZE) {
      showToast(`文件 ${file.name} 超过 10MB 限制`, 'error');
      continue;
    }

    // 3. 确保有会话
    let sessionId = currentSessionId.value;
    if (!sessionId) {
      if (USE_MOCK) {
        sessionId = `mock-session-${Date.now()}`;
        currentSessionId.value = sessionId;
        sessions.value.unshift({
          session_id: sessionId,
          title: '新对话',
          created_at: new Date().toISOString()
        });
      } else {
        try {
          const title = '新对话';
          const response = await api.createSession(userId, title);
          sessionId = response.data.session_id;
          currentSessionId.value = sessionId;
          await fetchSessions();
        } catch (error) {
          console.error('创建会话失败:', error);
          showToast('创建会话失败，请重试', 'error');
          continue;
        }
      }
    }

    // 4. 添加到 sessionDocuments（上传中状态）
    const tempId = `temp-${Date.now()}-${Math.random()}`;
    // 根据文件扩展名获取文档类型
    const fileExt = file.name.split('.').pop()?.toUpperCase() || '';
    const docTypeMap = {
      'PDF': 'PDF',
      'DOCX': 'DOCX',
      'DOC': 'DOCX',
      'TXT': 'TXT',
      'MD': 'MARKDOWN',
      'MARKDOWN': 'MARKDOWN',
      'PPTX': 'PPTX',
      'PPT': 'PPTX',
      'PNG': 'IMAGE',
      'JPG': 'IMAGE',
      'JPEG': 'IMAGE',
      'GIF': 'IMAGE',
      'WEBP': 'IMAGE',
    };
    const documentType = docTypeMap[fileExt] || null;
    
    const docEntry = {
      doc_id: tempId,
      file_name: file.name,
      document_type: documentType,
      status: 'UPLOADING',
      error_message: null,
      progress: 0,
      step: '上传中',
    };
    sessionDocuments.value.push(docEntry);

    // 5. 立即上传到后端
    const docUploadStart = Date.now();
    try {
      console.log(`[DocUpload] 开始上传文档: ${file.name}, 大小: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
      const result = await api.uploadSessionDocument(sessionId, file, (progressEvent) => {
        const idx = sessionDocuments.value.findIndex(d => d.doc_id === tempId);
        if (idx !== -1) {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          sessionDocuments.value[idx].progress = pct;
        }
      });

      const uploadElapsed = ((Date.now() - docUploadStart) / 1000).toFixed(2);
      console.log(`[DocUpload] 上传成功 | 文件: ${file.name} | 耗时: ${uploadElapsed}s | doc_id: ${result.doc_id}`);

      // 上传成功，更新 doc_id 和状态
      const idx = sessionDocuments.value.findIndex(d => d.doc_id === tempId);
      if (idx !== -1) {
        sessionDocuments.value[idx].doc_id = result.doc_id;
        sessionDocuments.value[idx].status = 'QUEUED';
        sessionDocuments.value[idx].progress = 5;
        sessionDocuments.value[idx].step = '排队中';
      }

      // 6. 建立 SSE 连接开始处理文档
      startDocumentProcessing(result.doc_id);
    } catch (error) {
      const uploadElapsed = ((Date.now() - docUploadStart) / 1000).toFixed(2);
      const errorDetail = error.response?.data?.detail || error.message || '未知错误';
      const isDuplicate = error.response?.status === 409;
      console.error(`[DocUpload] 上传失败 | 文件: ${file.name} | 耗时: ${uploadElapsed}s | 错误: ${errorDetail}`, error);
      const idx = sessionDocuments.value.findIndex(d => d.doc_id === tempId);
      if (idx !== -1) {
        // 重复文件直接移除卡片，不显示失败状态
        if (isDuplicate) {
          sessionDocuments.value.splice(idx, 1);
        } else {
          sessionDocuments.value[idx].status = 'FAILED';
          sessionDocuments.value[idx].error_message = errorDetail;
          sessionDocuments.value[idx].progress = 0;
          sessionDocuments.value[idx].step = '失败';
        }
      }
      showToast(isDuplicate ? errorDetail : `文档 ${file.name} 上传失败: ${errorDetail}`, 'error');
    }
  }

  // 清空文件输入
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

// SSE 连接管理
const sseConnections = ref({});

// 阶段时间统计
const stageTimings = ref({});

// 启动文档处理（SSE 方式）
const startDocumentProcessing = (docId) => {
  if (sseConnections.value[docId]) {
    console.log(`[SSE] 已存在连接 | doc_id: ${docId}`);
    return;
  }

  const processStart = Date.now();
  let lastStatus = null;
  let lastStatusTime = Date.now();
  
  // 初始化时间统计
  stageTimings.value[docId] = {};
  
  console.log(`[SSE] 开始处理文档 | doc_id: ${docId}`);

  const eventSource = api.processDocumentSSE(
    docId,
    'session',
    // onProgress: 进度更新回调
    (data) => {
      const now = Date.now();
      const idx = sessionDocuments.value.findIndex(d => d.doc_id === docId);
      
      // 统计上一个阶段的耗时
      if (lastStatus && lastStatus !== data.status) {
        const duration = ((now - lastStatusTime) / 1000).toFixed(2);
        stageTimings.value[docId][lastStatus] = duration;
        console.log(`[SSE] 阶段耗时 | doc_id: ${docId} | ${lastStatus} -> ${data.status} | 耗时: ${duration}s`);
      }
      
      lastStatus = data.status;
      lastStatusTime = now;
      
      if (idx !== -1) {
        console.log(`[SSE] 更新UI | doc_id: ${docId} | status: ${data.status} | step: ${data.step} | progress: ${data.progress}%`);
        sessionDocuments.value[idx].status = data.status;
        sessionDocuments.value[idx].progress = data.progress;
        sessionDocuments.value[idx].step = data.step;
        sessionDocuments.value[idx].error_message = data.error_message || null;
      }
    },
    // onComplete: 完成回调
    (data) => {
      const elapsed = ((Date.now() - processStart) / 1000).toFixed(2);
      
      // 打印完整的阶段耗时统计
      console.log(`[SSE] ========== 处理完成 ==========`);
      console.log(`[SSE] doc_id: ${docId}`);
      console.log(`[SSE] 总耗时: ${elapsed}s`);
      console.log(`[SSE] 各阶段耗时:`, stageTimings.value[docId]);
      console.log(`[SSE] ================================`);
      
      delete sseConnections.value[docId];
      delete stageTimings.value[docId];

      if (data.status === 'COMPLETED') {
        // 文档处理完成，同步更新右上角面板的 allSessionDocuments
        const idx = sessionDocuments.value.findIndex(d => d.doc_id === docId);
        if (idx !== -1) {
          const doc = sessionDocuments.value[idx];
          const alreadyExists = allSessionDocuments.value.some(d => d.doc_id === docId);
          if (!alreadyExists) {
            allSessionDocuments.value.push({
              doc_id: doc.doc_id,
              file_name: doc.file_name,
              document_type: doc.document_type,
              status: 'COMPLETED',
            });
          }
        }
      } else if (data.status === 'FAILED') {
        const idx = sessionDocuments.value.findIndex(d => d.doc_id === docId);
        if (idx !== -1) {
          showToast(`文档 ${sessionDocuments.value[idx].file_name} 处理失败: ${data.error_message || '未知错误'}`, 'error');
        }
      }
    },
    // onError: 错误回调
    (error) => {
      console.error(`[SSE] 连接错误 | doc_id: ${docId}`, error);
      delete sseConnections.value[docId];
      delete stageTimings.value[docId];
      const idx = sessionDocuments.value.findIndex(d => d.doc_id === docId);
      if (idx !== -1) {
        sessionDocuments.value[idx].status = 'FAILED';
        sessionDocuments.value[idx].error_message = '连接中断';
        sessionDocuments.value[idx].progress = 0;
        sessionDocuments.value[idx].step = '失败';
      }
    }
  );

  sseConnections.value[docId] = eventSource;
};

// 关闭所有 SSE 连接
const closeAllSSEConnections = () => {
  Object.entries(sseConnections.value).forEach(([docId, eventSource]) => {
    console.log(`[SSE] 关闭连接 | doc_id: ${docId}`);
    eventSource.close();
  });
  sseConnections.value = {};
};

// 触发菜单下拉
const triggerImageUploadFromMenu = () => {
  showMenuDropdown.value = false; // 关闭菜单
  triggerImageUpload(); // 触发图片上传
};

// 切换上传菜单并计算位置
const toggleUploadMenu = () => {
  showMenuDropdown.value = !showMenuDropdown.value;
  if (showMenuDropdown.value) {
    nextTick(() => {
      updateUploadMenuPosition();
    });
  }
};

// 更新上传菜单位置
const updateUploadMenuPosition = () => {
  if (uploadMenuButton.value) {
    const rect = uploadMenuButton.value.getBoundingClientRect();
    uploadMenuStyle.value = {
      bottom: `${window.innerHeight - rect.top + 8}px`,
      left: `${rect.left}px`
    };
  }
};

// 更新输入框区域高度，动态调整消息容器的底部内边距
const updateInputAreaHeight = () => {
  if (inputAreaRef.value) {
    const height = inputAreaRef.value.offsetHeight;
    // 添加额外的20px作为缓冲，确保消息不会被遮挡
    dynamicPaddingBottom.value = `${height + 20}px`;
  }
};

// 点击外部关闭菜单
const handleClickOutside = (e) => {
  if (showMenuDropdown.value) {
    // 检查点击是否在按钮或菜单内部
    const isClickInsideButton = uploadMenuButton.value && uploadMenuButton.value.contains(e.target);
    const isClickInsideMenu = uploadMenu.value && uploadMenu.value.contains(e.target);
    
    // 如果点击在按钮和菜单外部，则关闭菜单
    if (!isClickInsideButton && !isClickInsideMenu) {
      showMenuDropdown.value = false;
    }
  }
};

// ResizeObserver 实例
let inputAreaResizeObserver = null;

onMounted(() => {
  fetchSessions();
  fetchChatModels();  // 加载模型列表
  
  // 添加全局点击事件监听
  document.addEventListener('click', handleClickOutside);
  document.addEventListener('click', handleKbSelectorClickOutside);
  
  // 初始化输入框高度和自动聚焦
  nextTick(() => {
    updateInputAreaHeight();
    
    // 使用 ResizeObserver 监听输入框区域高度变化
    if (inputAreaRef.value) {
      inputAreaResizeObserver = new ResizeObserver(() => {
        updateInputAreaHeight();
      });
      inputAreaResizeObserver.observe(inputAreaRef.value);
    }
    
    // 页面加载完成后自动聚焦输入框
    textareaRef.value?.focus();
  });
});

onUnmounted(() => {
  console.log('[Chat] 组件卸载，清理资源');
  
  // 1. 移除事件监听
  document.removeEventListener('click', handleClickOutside);
  document.removeEventListener('click', handleKbSelectorClickOutside);
  
  // 2. 清理 ResizeObserver
  if (inputAreaResizeObserver) {
    inputAreaResizeObserver.disconnect();
    inputAreaResizeObserver = null;
  }
  
  // 3. 中断正在进行的请求（关键！防止幽灵请求）
  if (abortController.value) {
    console.log('[Chat] 中断未完成的请求');
    abortController.value.abort();
    abortController.value = null;
  }
  
  // 3.1 中断 Mock 流
  if (mockStreamController) {
    mockStreamController.abort();
    mockStreamController = null;
  }
  
  // 4. 重置所有状态
  isLoading.value = false;
  sendLock.value = false;
  chatReferences.reset();
  
  // 4.1 清理 SSE 连接
  closeAllSSEConnections();
  sessionDocuments.value = [];
  allSessionDocuments.value = [];
  
  // 5. 清理图片预览 URL（防止内存泄漏）
  pendingImages.value.forEach(img => {
    if (img.previewUrl) {
      URL.revokeObjectURL(img.previewUrl);
    }
  });
  pendingImages.value = [];
});

watch(userInput, autoGrowTextarea);
</script>

<style scoped>

.overflow-y-auto {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
}
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.8);
}

/* 浏览器兼容性 - 确保输入框字体在Chrome和Edge中显示一致 */
textarea {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  font-feature-settings: "kern" 1;
}

/* textarea滚动条样式 */
.textarea-scrollable {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
}

.textarea-scrollable::-webkit-scrollbar {
  width: 6px;
}

.textarea-scrollable::-webkit-scrollbar-track {
  background: transparent;
}

.textarea-scrollable::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}

.textarea-scrollable::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.8);
}

.animate-fade-in {
  animation: fadeIn 0.6s ease-out;
}
.animate-slide-in {
  animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
textarea:focus + .absolute {
  background: linear-gradient(90deg, transparent, theme('colors.blue.400'), transparent);
  opacity: 0.6;
  transition: opacity 0.3s ease;
}
@media (max-width: 768px) {
  .absolute.bottom-0 {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}
</style>